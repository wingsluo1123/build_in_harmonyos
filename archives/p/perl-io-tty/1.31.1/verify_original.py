"""All nine original tests, retaining64 assertion inventory and exactly2 accepted guards."""
import hashlib,json,re
from pathlib import Path
def verify(source,out,rc):
 spec=json.loads((source/'original-tests.json').read_bytes());declared=spec['files'];actual={p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (source/'t').glob('*.t')};stdout=(out/'stdout').read_text(encoding='utf8');stderr=(out/'stderr').read_text(encoding='utf8');summary=re.findall(r'Files=(\d+),\s*Tests=(\d+)',stdout+'\n'+stderr);current=None;per_file={};todo=[];failed=[]
 for line in stdout.splitlines():
  m=re.match(r'^t[/\\]([^\s]+\.t)\s+\.{2,}(?:\s|$)',line)
  if m:
   current='t/'+m[1];assert current in declared and current not in per_file;per_file[current]={'assertions':[],'skips':[],'reasons':[],'plans':[]};continue
  if re.search(r'#\s*TODO\b',line,re.I):todo.append(line)
  if re.match(r'^not ok\b|^Bail out!',line):failed.append(line)
  m=re.match(r'^1\.\.(\d+)(?:\s|$)',line)
  if m:
   assert current;per_file[current]['plans'].append(int(m[1]))
  m=re.match(r'^ok\s+(\d+)(?:\s|$)',line)
  if m:
   assert current;number=int(m[1]);per_file[current]['assertions'].append(number);skip=re.search(r'#\s*skip\b\s*(.*)',line,re.I)
   if skip:per_file[current]['skips'].append(number);per_file[current]['reasons'].append(skip[1].strip())
 accepted=spec['accepted_not_applicable'];expected={'t/clone_winsize.t':[5],'t/pty_set_raw.t':[14]};assert {p:v['assertions'] for p,v in accepted.items()}==expected
 counts_ok=set(per_file)==set(declared)
 for path,values in per_file.items():
  expected_count=spec['planned_counts'][path];rule=accepted.get(path);skips=rule['assertions'] if rule else []
  counts_ok=counts_ok and values['plans']==[expected_count] and values['assertions']==list(range(1,expected_count+1)) and values['skips']==skips and values['reasons']==([rule['raw_reason']]*len(skips) if rule else [])
 value={'source_files':actual,'source_file_count':len(actual),'source_hashes_unchanged':actual==declared,'rc':rc,'summary':summary,'actual_assertions':64 if summary==[('9','64')] else None,'registered_assertions':64,'passed_applicable_assertions':sum(len(v['assertions'])-len(v['skips']) for v in per_file.values()),'accepted_not_applicable_count':sum(len(v['skips']) for v in per_file.values()),'per_file':per_file,'raw_original_guard_skips_preserved':True,'todo_lines':todo,'failed_assertions':failed,'full64_pass':False,'stdout_sha256':hashlib.sha256((out/'stdout').read_bytes()).hexdigest(),'stderr_sha256':hashlib.sha256((out/'stderr').read_bytes()).hexdigest()}
 value['applicable_original_pass']=bool(len(actual)==9 and actual==declared and rc==0 and summary==[('9','64')] and counts_ok and value['passed_applicable_assertions']==62 and value['accepted_not_applicable_count']==2 and not todo and not failed and 'All tests successful.' in stdout)
 with (out/'result.json').open('x',encoding='utf8') as f:json.dump(value,f,indent=2)
 if not value['applicable_original_pass']:raise RuntimeError('Original IO::Tty applicability incomplete; only exact two accepted guards allowed, full raw outcomes retained')
 return value
