"""Bind actual original source programs and TAP without denominator reduction."""
import hashlib,json,re
FILES=frozenset(('00-load.t','00-report-prereqs.t','01-basic.t'))
def verify(source,out,rc):
    actual={p.name for p in (source/'t').glob('*.t')}
    stdout=(out/'stdout').read_text(encoding='utf8');stderr=(out/'stderr').read_text(encoding='utf8');text=stdout+'\n'+stderr
    if actual!=FILES or rc or re.search(r'^not ok\b|^Bail out!|#[ \t]*(?:SKIP|TODO)\b',text,re.M|re.I):raise RuntimeError('Original B::COW failed, skipped or source drifted')
    files=re.findall(r'^t[/\\]([0-9a-z_-]+\.t)\b',stdout,re.M);plans=[int(x) for x in re.findall(r'^1\.\.(\d+)[ \t]*$',stdout,re.M)];rows=re.findall(r'^ok[ \t]+\d+(?:[ \t]+[^\r\n]*)?$',stdout,re.M)
    if len(files)!=3 or set(files)!=FILES or len(plans)!=3 or sum(plans)!=22 or len(rows)!=22 or not re.search(r'Files=3,[ \t]*Tests=22\b',text) or 'All tests successful.' not in text:raise RuntimeError('Incomplete original source/TAP')
    value={'source_files':sorted(actual),'source_file_count':3,'actual_passed_assertions':22,'skip':0,'rc':rc,'files_are_not_assertion_count':True,'stdout_sha256':hashlib.sha256((out/'stdout').read_bytes()).hexdigest(),'stderr_sha256':hashlib.sha256((out/'stderr').read_bytes()).hexdigest()}
    with (out/'result.json').open('x',encoding='utf8') as f:json.dump(value,f,sort_keys=True)
