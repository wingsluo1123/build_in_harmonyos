"""Preserve source-file and assertion denominators independently."""
import hashlib
import json
import re
FILES = frozenset(('cmn.t','dependency.t','import_error.t','ivmn.t','ivms.t','mnf.t','rm.t','taint.t','um.t','upo.t','upo_overridden.t'))
def verify(source, out, rc):
    actual = {p.name for p in (source / 't').glob('*.t')}
    if actual != FILES:
        raise RuntimeError('Original Module::Runtime source inventory drift')
    stdout = (out / 'stdout').read_text(encoding='utf8')
    stderr = (out / 'stderr').read_text(encoding='utf8')
    text = stdout + '\n' + stderr
    if rc or re.search(r'^not ok\b|^Bail out!|#[ \t]*(?:SKIP|TODO)\b', text, re.M | re.I):
        raise RuntimeError('Original CPAN command failed or skipped')
    files = re.findall(r'^t[/\\]([a-z_]+\.t)\b', stdout, re.M)
    plans = [int(n) for n in re.findall(r'^1\.\.(\d+)[ \t]*$', stdout, re.M)]
    rows = re.findall(r'^ok[ \t]+\d+(?:[ \t]+[^\r\n]*)?$', stdout, re.M)
    if len(files) != 11 or set(files) != FILES or not re.search(r'Files=11,[ \t]*Tests=365\b', text):
        raise RuntimeError('Incomplete original file denominator')
    if len(plans) != 11 or sum(plans) != 365 or len(rows) != 365 or 'All tests successful.' not in text:
        raise RuntimeError('Incomplete original TAP')
    value = {'source_files': sorted(actual), 'source_file_count': 11, 'actual_passed_assertions': 365,
             'skip': 0, 'rc': rc, 'files_are_not_assertion_count': True,
             'stdout_sha256': hashlib.sha256((out / 'stdout').read_bytes()).hexdigest(),
             'stderr_sha256': hashlib.sha256((out / 'stderr').read_bytes()).hexdigest()}
    with (out / 'result.json').open('x', encoding='utf8') as stream:
        json.dump(value, stream, sort_keys=True)
