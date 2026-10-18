"""Observe unmodified pytest outcomes; allow only the explicitly accepted version guard."""
import hashlib,json,os,sys
from pathlib import Path
import pytest
source=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();spec=json.loads((source/'original-tests.json').read_bytes());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sys.version_info[:3]==(3,12,9) and len(spec['files'])==7 and all(sha(source/p)==h for p,h in spec['files'].items())
os.chdir(source);os.environ['FLIT_NATIVE_OBSERVATION']=str(out/'observation.json')
rc=pytest.main(['-vv','-ra','--tb=short','-p','native_observation','tests_core']);v=json.loads((out/'observation.json').read_bytes());node=spec['accepted_original_version_guard']['nodeid'];reason=spec['accepted_original_version_guard']['raw_reason'];ids=v['collected_nodeids'];by={n:[] for n in ids}
for r in v['reports']:by[r['nodeid']].append(r)
assert ids==spec['collected_nodeids'] and len(ids)==len(set(ids))==219 and {n.split('::')[0] for n in ids}==set(spec['files'])
assert rc==v['exitstatus']==0 and all(r['outcome']=='passed' for r in v['collection'])
for n,rows in by.items():
    assert all(not r['wasxfail'] for r in rows)
    phases=[r['when'] for r in rows]
    if n==node:
        assert phases==['setup','teardown'] and rows[0]['outcome']=='skipped' and rows[0]['skip_reason']==reason and rows[1]['outcome']=='passed'
    else:assert phases==['setup','call','teardown'] and all(r['outcome']=='passed' for r in rows)
assert all(sha(source/p)==h for p,h in spec['files'].items())
result={'status':'APPLICABLE_PASS_WITH_EXACT_ORIGINAL_VERSION_GUARD','rc':rc,'original_programs':7,'registered_cases':219,'applicable_passed':218,'accepted_not_applicable':1,'exact_nodeid':node,'raw_reason':reason,'other_skip_xfail_failed':0,'source_test_hashes':spec['files'],'source_tests_unchanged':True,'observation_sha256':sha(out/'observation.json')}
(out/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
