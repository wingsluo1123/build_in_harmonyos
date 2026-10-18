"""Source-bound full original EUMM/TAP evidence, with no skipped assertions."""
import hashlib,json,re
def verify(source,out,rc):
    lock=json.loads((source/'original-source-tests.json').read_text(encoding='utf8'))
    expected=dict(lock['source_files']);expected.update(lock['adapted_source_files']);actual={p.relative_to(source).as_posix() for p in (source/'t').glob('*.t')}
    if actual!=set(expected) or any(hashlib.sha256((source/n).read_bytes()).hexdigest()!=h for n,h in expected.items()):raise RuntimeError('Original source test inventory/hash drift')
    stdout=(out/'stdout').read_text(encoding='utf8');stderr=(out/'stderr').read_text(encoding='utf8');text=stdout+'\n'+stderr
    if rc or re.search(r'^not ok\b|^Bail out!|#[ \t]*(?:SKIP|TODO)\b',text,re.M|re.I):raise RuntimeError('Original tests failed or remain uncovered')
    match=re.search(r'Files=(\d+),[ \t]*Tests=(\d+)\b',text);files=re.findall(r'^t[/\\]([^\r\n ]+\.t)\b',stdout,re.M);plans=[int(x) for x in re.findall(r'^1\.\.(\d+)[ \t]*$',stdout,re.M)];rows=re.findall(r'^ok[ \t]+\d+(?:[ \t]+[^\r\n]*)?$',stdout,re.M)
    if not match or int(match[1])!=len(expected) or len(files)!=len(expected) or {'t/'+x for x in files}!=set(expected) or len(plans)!=len(expected) or sum(plans)!=int(match[2]) or len(rows)!=int(match[2]) or 'All tests successful.' not in text:raise RuntimeError('Incomplete original full TAP aggregation')
    value={'source_files':lock['source_files'],'adapted_source_files':lock['adapted_source_files'],'source_file_count':len(expected),'executed_source_file_count':len(expected),'full_upstream_pass':True,'original_test_modified':True,'actual_passed_assertions':int(match[2]),'skip':0,'todo':0,'rc':rc,'files_are_not_assertion_count':True,'stdout_sha256':hashlib.sha256((out/'stdout').read_bytes()).hexdigest(),'stderr_sha256':hashlib.sha256((out/'stderr').read_bytes()).hexdigest()}
    (out/'result.json').write_text(json.dumps(value,sort_keys=True),encoding='utf8');return value
