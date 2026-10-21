"""Validate the exact unchanged original Canary suite and real TAP outputs."""
import hashlib,json,re
def verify(source,out,rc):
    lock=json.loads((source/'original-source-tests.json').read_bytes());expected=lock['source_files']
    assert set(expected)=={'t/00_load.t'} and {p.relative_to(source).as_posix() for p in (source/'t').glob('*.t')}==set(expected)
    assert all(hashlib.sha256((source/n).read_bytes()).hexdigest()==h for n,h in expected.items()),'ORIGINAL_SOURCE_DRIFT'
    stdout=(out/'stdout').read_text();stderr=(out/'stderr').read_text();text=stdout+'\n'+stderr
    assert rc==0 and not re.search(r'^not ok\b|^Bail out!|#\s*(?:SKIP|TODO)\b',text,re.M|re.I),'ORIGINAL_TEST_FAILURE_OR_SKIP'
    files=re.findall(r'^t[/\\]([^\r\n ]+\.t)\b',stdout,re.M);assert files==['00_load.t']
    plans=re.findall(r'^1\.\.(\d+)[ \t]*$',stdout,re.M);rows=re.findall(r'^ok\s+\d+(?:[ \t]+[^\r\n]*)?$',stdout,re.M)
    assert plans==['1'] and len(rows)==1 and re.search(r'Files=1,\s*Tests=1\b',text) and 'All tests successful.' in text
    value={'source_files':expected,'source_file_count':1,'actual_passed_assertions':1,'skip':0,'todo':0,'rc':rc,'full_upstream_pass':True,'stdout_sha256':hashlib.sha256((out/'stdout').read_bytes()).hexdigest(),'stderr_sha256':hashlib.sha256((out/'stderr').read_bytes()).hexdigest()}
    (out/'result.json').write_text(json.dumps(value,sort_keys=True));return value
