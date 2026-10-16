"""Verify every official Net::Daemon program and retain the root-only branch."""
import hashlib,json,re

def verify(source,out,rc):
    manifest=json.loads((source/'original-source-inventory.json').read_text(encoding='utf8'))
    expected=manifest['original_tests']
    actual={'t/'+p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (source/'t').glob('*.t')}
    if actual!={n:v['sha256'] for n,v in expected.items()}:
        raise RuntimeError('Original source inventory or test bytes changed')
    stdout=(out/'stdout').read_text(encoding='utf8');stderr=(out/'stderr').read_text(encoding='utf8')
    if rc or 'All tests successful.' not in stdout+stderr:
        raise RuntimeError('Original make test did not succeed')
    headers=list(re.finditer(r'(?m)^(t/[a-zA-Z0-9_-]+\.t)\s+\.{2,}[^\n]*',stdout))
    if len(headers)!=18 or {h[1] for h in headers}!=set(expected):
        raise RuntimeError('Missing, duplicated or unknown original program output')
    programs=[];capabilities=[]
    for index,header in enumerate(headers):
        text=stdout[header.end():headers[index+1].start() if index+1<len(headers) else len(stdout)]
        plans=re.findall(r'(?m)^1\.\.(\d+)(?:\s*#[^\n]*)?\s*$',text)
        points=list(re.finditer(r'(?m)^(not )?ok\s+(\d+)\b([^\n]*)',text))
        if len(plans)!=1 or int(plans[0])<=0 or len(points)!=int(plans[0]):
            raise RuntimeError('Missing plan or original assertion output: '+header[1])
        if [int(p[2]) for p in points]!=list(range(1,len(points)+1)):
            raise RuntimeError('Original assertion identity drift: '+header[1])
        skipped=[]
        for point in points:
            if point[1] or re.search(r'#\s*TODO\b',point[3],re.I):
                raise RuntimeError('Original failure or unaccepted TODO: '+header[1])
            if re.search(r'#\s*SKIP\b',point[3],re.I):
                allowed={
                    ('t/privdrop.t',3):('Requires root on Linux to test saved-set-user-ID','ACCOUNT_PRIVILEGE_UNAVAILABLE'),
                    ('t/mode.t',3):('Only verifiable on Perl < 5.10','ABI_NOT_APPLICABLE'),
                    ('t/mode.t',4):('Only verifiable on MSWin32','ABI_NOT_APPLICABLE'),
                }
                key=(header[1],int(point[2]))
                if key not in allowed or allowed[key][0] not in point[3]:
                    raise RuntimeError('Unexpected original skip: '+header[1])
                reason,kind=allowed[key]
                skipped.append({'assertion':int(point[2]),'reason':reason,'actual_output':point[0]})
                capabilities.append({'program':header[1],'assertion':int(point[2]),'reason':reason,'type':kind,'original_source_sha256':actual[header[1]]})
        programs.append({'file':header[1],'total':len(points),'passed':len(points)-len(skipped),'skipped':skipped,'source_sha256':actual[header[1]]})
    if len(capabilities)!=3:
        raise RuntimeError('Root privilege boundary changed; explicit reassessment required')
    total=sum(x['total'] for x in programs);passed=sum(x['passed'] for x in programs)
    value={'original_programs':18,'clean_programs':16,'partial_programs':2,'original_assertions':total,'passed_assertions':passed,'skipped_assertions':3,'failed_assertions':0,'original_passed':False,'full_upstream_pass':False,'capability_exceptions':capabilities,'programs':programs,'make_test_rc':rc,'stdout_sha256':hashlib.sha256((out/'stdout').read_bytes()).hexdigest(),'stderr_sha256':hashlib.sha256((out/'stderr').read_bytes()).hexdigest()}
    (out/'summary.json').write_text(json.dumps(value,indent=2),encoding='utf8')
    return value
