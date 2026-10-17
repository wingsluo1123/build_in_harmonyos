"""Record all original Taint::Runtime files and actual TAP; no inferred skip waiver."""
import hashlib,json,re
from pathlib import Path
def verify(source,out,rc):
    declared=json.loads((source/'original-tests.json').read_bytes())['files']
    actual={p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (source/'t').glob('*.t')}
    stdout=(out/'stdout').read_text(encoding='utf8');stderr=(out/'stderr').read_text(encoding='utf8');text=stdout+'\n'+stderr
    summary=re.findall(r'Files=(\d+),\s*Tests=(\d+)',text)
    files=re.findall(r'^t[/\\]([^\s]+\.t)\b',stdout,re.M)
    directives=[line for line in text.splitlines() if re.search(r'#[ \t]*(?:SKIP|TODO)\b',line,re.I)]
    value={'source_files':actual,'source_file_count':len(actual),'source_hashes_unchanged':actual==declared,'rc':rc,'summary':summary,'actual_assertions':int(summary[-1][1]) if summary else None,'skip_todo_lines':directives,'reported_source_programs':files,'stdout_sha256':hashlib.sha256((out/'stdout').read_bytes()).hexdigest(),'stderr_sha256':hashlib.sha256((out/'stderr').read_bytes()).hexdigest()}
    value['full_pass']=bool(len(actual)==6 and actual==declared and rc==0 and summary and int(summary[-1][0])==6 and len(files)==6 and set(files)=={Path(n).name for n in declared} and not directives and not re.search(r'^not ok\b|^Bail out!',text,re.M) and 'All tests successful.' in text)
    with (out/'result.json').open('x',encoding='utf8') as f:json.dump(value,f,indent=2)
    if not value['full_pass']:raise RuntimeError('Original Taint::Runtime coverage not complete; exact all-6 TAP outcomes retained without waiver')
    return value
