"""Materialize the real release benchmark inputs, never reduced fixtures."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import tarfile

from conan.tools.files import check_sha256, download

CORPORA = (
    ('boost_1_58_0.tar.gz', 'https://archives.boost.io/release/1.58.0/source/boost_1_58_0.tar.gz',
     'a004d9b3fa95e956383693b86fce1b68805a6f71c2e68944fa813de0fb8c8102', 'boost_1_58_0'),
    ('linux-4.8.tar.xz', 'https://cdn.kernel.org/pub/linux/kernel/v4.x/linux-4.8.tar.xz',
     '3e9150065f193d3d94bcf46a1fe9f033c7ef7122ab71d75a7fb5a2f0c9a7e11a', 'linux-4.8'),
    ('OpenSubtitles2016.en.txt.gz', 'https://object.pouta.csc.fi/OPUS-OpenSubtitles/v2016/mono/en.txt.gz',
     '7c169ffa7742fd7f670c176ba8c290b74bcc650784e585e2ef60061376c8fff1', None),
)
SUBTITLE_BYTES = 9968530111
SUBTITLE_SHA256 = 'a84b1e0c66645c429ff356510dc872d5d9cca1c5a02a21d6eee3cff24d4781bb'


def plain_path(path):
    path = Path(os.path.abspath(path))
    for parent in (path, *path.parents):
        if parent.is_symlink() or (hasattr(parent, 'is_junction') and parent.is_junction()):
            raise RuntimeError('Redirected corpus path: ' + str(parent))
    return path


def prepare_corpora(recipe):
    # Original tests use ../TestCorpus relative to the Conan build/source root.
    # Each Conan build has its own parent and hence no shared corpus directory.
    root = plain_path(Path(recipe.build_folder).parent / 'TestCorpus')
    if root.exists():
        raise RuntimeError('Corpus root already exists; use a fresh build folder')
    root.mkdir()
    local = recipe.conf.get('user.ucg:corpus_archives', default=None)
    inputs = plain_path(local) if local else root / 'archives'
    if not local:
        inputs.mkdir()
    records = []
    for name, url, sha, member_root in CORPORA:
        archive = plain_path(inputs / name)
        if not local:
            download(recipe, url, str(archive))
        check_sha256(recipe, str(archive), sha)
        records.append({'url': url, 'file': name, 'sha256': sha, 'bytes': archive.stat().st_size})
        if member_root:
            with tarfile.open(archive) as tar:
                members = tar.getmembers()
                if sum(m.size for m in members) > 8 * 1024**3:
                    raise RuntimeError('Unexpected corpus archive expansion')
                if any(m.name.split('/')[0] != member_root for m in members):
                    raise RuntimeError('Unexpected corpus archive root')
                tar.extractall(root, members=members, filter='data')
            if member_root == 'linux-4.8':
                (root / member_root).rename(root / 'linux')
        else:
            subtitles = root / 'subtitles'
            subtitles.mkdir()
            digest = hashlib.sha256()
            size = 0
            with gzip.open(archive, 'rb') as source, (subtitles / 'OpenSubtitles2016.raw.en.disable').open('xb') as output:
                while block := source.read(1024 * 1024):
                    size += len(block)
                    if size > SUBTITLE_BYTES:
                        raise RuntimeError('Unexpected subtitle expansion')
                    digest.update(block)
                    output.write(block)
            if size != SUBTITLE_BYTES or digest.hexdigest() != SUBTITLE_SHA256:
                raise RuntimeError('Incomplete or changed subtitle corpus')
    with (root / 'inputs.json').open('x', encoding='utf-8') as out:
        json.dump(records, out, indent=2)
    recipe.output.info('UCG_CORPUS_RESULT=all three official archives verified; full subtitle bytes=' + str(SUBTITLE_BYTES))


def validate_autotest(summary):
    results = {}
    for match in re.finditer(r'(?m)^(\d+)\. .+ \([^\n()]+\.at:\d+\): (ok|expected failure|FAILED|UNEXPECTED PASS|skipped)(?:\s|\(|$)', summary):
        number, outcome = int(match[1]), match[2]
        if number in results and results[number] != outcome:
            raise RuntimeError('Contradictory Autotest outcome')
        results[number] = outcome
    expected = {i: 'expected failure' if i in (28, 30) else 'ok' for i in range(1, 62)}
    if results != expected or 'All 61 tests behaved as expected.' not in summary:
        raise RuntimeError('Full Autotest inventory must be 59 PASS, original XFAIL 28/30, zero skipped/unexpected outcomes')
    # A generic XFAIL label would also accept a crash. Bind the two original
    # documented glob-precedence mismatches and reject unrelated failures.
    for number, wanted, actual, line in ((28, 5, 0, 143), (30, 0, 5, 181)):
        marker = f'./testsuite.dir/{number}/testsuite.log'
        if summary.count(marker) != 1:
            raise RuntimeError('Missing/duplicate original XFAIL detail')
        detail = summary.split(marker, 1)[1].split('./testsuite.dir/', 1)[0]
        if (f'expected failure (type_inclusion.at:{line})' not in detail
                or not re.search(r'(?m)^stderr:\s*\n--- ', detail)
                or f'\n-{wanted}\n+{actual}\n' not in detail
                or re.search(r'(?i)segmentation|signal|core dump|sanitizer|exit code was|aborted|not found', detail)):
            raise RuntimeError('XFAIL is not the original controlled glob-precedence result')
    return results
