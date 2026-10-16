"""Retain all 28 originals; accept only two explicitly authorized platform guards."""
import hashlib,json,os,re

def verify(source,out,rc):
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    lock=json.loads((source/'original-source-tests.json').read_bytes());expected=lock['source_files'];actual={'t/'+p.name for p in (source/'t').glob('*.t')}
    assert len(expected)==28 and actual==set(expected),'ORIGINAL_REGISTRY_DRIFT'
    assert all(digest(source/n)==v for n,v in {**expected,**lock['support_files']}.items()),'ORIGINAL_BYTES_DRIFT'
    policy=json.loads((source/'platform-not-applicable.json').read_bytes());na={x['path']:x for x in policy['not_applicable']}
    assert set(na)=={'t/12_bug_47223.t','t/28_zip64_unsupported.t'} and policy['registered_programs']==28 and policy['applicable_programs']==26 and policy['expected_applicable_assertions']==911 and not policy['allow_other_skips']
    assert all(expected[n]==v['sha256']==lock['original_unmodified_members'][n] for n,v in na.items()),'NOT_APPLICABLE_SOURCE_DRIFT'
    platform=json.loads((out/'platform.json').read_bytes());assert os.uname().sysname=='HarmonyOS' and os.uname().machine=='aarch64' and platform['perl_os']!='MSWin32' and platform['zip64_supported']==1 and platform['pointer_bytes']==8,'ACTUAL_PLATFORM_GUARD_NOT_PROVEN'
    stdout=(out/'stdout').read_text(encoding='utf8');stderr=(out/'stderr').read_text(encoding='utf8');text=stdout+'\n'+stderr
    headers=list(re.finditer(r'^t[/\\]([A-Za-z0-9_-]+\.t)\b[^\r\n]*',stdout,re.M));files=['t/'+m[1] for m in headers];cases=[]
    for i,m in enumerate(headers):
        name='t/'+m[1];segment=stdout[m.end():headers[i+1].start() if i+1<len(headers) else len(stdout)]
        plans=[int(n) for n in re.findall(r'^1\.\.(\d+)(?:[ \t]+#[^\r\n]*)?[ \t]*$',segment,re.M)]
        rows=re.findall(r'^ok[ \t]+\d+(?:[ \t]+[^\r\n]*)?$',segment,re.M)
        skipped=re.search(r'\bskipped:[ \t]*(.*)$',m.group(0))
        cases.append({'path':name,'header':m.group(0),'plans':plans,'assertions':len(rows),'disposition':'PLATFORM_NOT_APPLICABLE_NOT_PASS' if skipped else 'APPLICABLE','reason':skipped[1].strip() if skipped else None})
    excluded=[x for x in cases if x['disposition']=='PLATFORM_NOT_APPLICABLE_NOT_PASS'];applicable=[x for x in cases if x['disposition']=='APPLICABLE']
    exact_na=len(excluded)==2 and {x['path'] for x in excluded}==set(na) and all(x['reason']==na[x['path']]['reason'] and not x['plans'] and x['assertions']==0 for x in excluded)
    bad=re.findall(r'^not ok\b[^\r\n]*|^Bail out![^\r\n]*',text,re.M);skip_directives=re.findall(r'^[^\r\n]*#[ \t]*(?:SKIP|TODO)\b[^\r\n]*',stdout,re.M|re.I)
    skipped_rows=re.findall(r'^ok[^\r\n]*#[ \t]*SKIP\b[^\r\n]*',stdout,re.M|re.I)
    summary=re.search(r'Files=(\d+),[ \t]*Tests=(\d+)\b',text)
    complete=bool(rc==0 and summary and int(summary[1])==28 and len(files)==28 and set(files)==actual and exact_na and len(applicable)==26 and all(len(x['plans'])==1 and x['plans'][0]>0 and x['plans'][0]==x['assertions'] for x in applicable) and sum(x['assertions'] for x in applicable)==int(summary[2])==911 and not bad and not skip_directives and not stderr and 'All tests successful.' in text)
    v={'source_files':expected,'source_file_count':28,'registered_programs':28,'applicable_programs':26,'actual_file_headers':files,'case_results':cases,'harness_summary':summary.group(0) if summary else None,'actual_passed_assertions':sum(x['assertions'] for x in applicable),'not_applicable':excluded,'skip':len(skipped_rows),'todo':sum(bool(re.search(r'#[ \t]*TODO\b',x,re.I)) for x in skip_directives),'skipped_assertion_rows':len(skipped_rows),'skip_todo_directives':skip_directives,'failed_tap':bad,'rc':rc,'full_global_upstream_pass':False,'applicable_upstream_pass':complete,'authorized_exact_not_applicable_count':2,'platform':platform,'policy_sha256':digest(source/'platform-not-applicable.json'),'stdout_sha256':digest(out/'stdout'),'stderr_sha256':digest(out/'stderr')}
    with (out/'result.json').open('x',encoding='utf8') as f:json.dump(v,f,sort_keys=True)
    if not complete:raise RuntimeError('APPLICABLE_ORIGINAL_SUITE_FAILED_OR_SCOPE_DRIFT: see actual full TAP and result.json')
    return v
