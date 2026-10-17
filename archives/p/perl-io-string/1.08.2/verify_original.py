"""Preserve source-file and assertion denominators independently."""
import hashlib
import json
import re
FILES = frozenset(('close.t', 'para.t', 'read.t', 'seek.t', 'truncate.t', 'write.t'))
def verify(source, out, rc):
    actual = {p.name for p in (source / 't').glob('*.t')}
    if actual != FILES:
        raise RuntimeError('Original IO::String source inventory drift')
    expected = json.loads((source / 'original-source-tests.json').read_bytes())['source_files']
    if set(expected) != {'t/' + name for name in FILES} or any(hashlib.sha256((source/name).read_bytes()).hexdigest() != value for name,value in expected.items()):
        raise RuntimeError('Original source hash drift')
    stdout = (out / 'stdout').read_text(encoding='utf8')
    stderr = (out / 'stderr').read_text(encoding='utf8')
    text = stdout + '\n' + stderr
    if rc or re.search(r'^not ok\b|^Bail out!|#[ \t]*(?:SKIP|TODO)\b', text, re.M | re.I):
        raise RuntimeError('Original CPAN command failed or skipped')
    files = re.findall(r'^t[/\\]([a-z]+\.t)\b', stdout, re.M)
    plans = [int(n) for n in re.findall(r'^1\.\.(\d+)[ \t]*$', stdout, re.M)]
    rows = re.findall(r'^ok[ \t]+\d+(?:[ \t]+[^\r\n]*)?$', stdout, re.M)
    if len(files) != 6 or set(files) != FILES or not re.search(r'Files=6,[ \t]*Tests=43\b', text):
        raise RuntimeError('Incomplete original file denominator')
    if len(plans) != 6 or sum(plans) != 43 or len(rows) != 43 or 'All tests successful.' not in text:
        raise RuntimeError('Incomplete original TAP')
    value = {'source_files': expected, 'source_file_count': 6, 'actual_passed_assertions': 43,
             'skip': 0, 'todo': 0, 'rc': rc, 'full_upstream_pass': True, 'files_are_not_assertion_count': True,
             'stdout_sha256': hashlib.sha256((out / 'stdout').read_bytes()).hexdigest(),
             'stderr_sha256': hashlib.sha256((out / 'stderr').read_bytes()).hexdigest()}
    with (out / 'result.json').open('x', encoding='utf8') as stream:
        json.dump(value, stream, sort_keys=True)
