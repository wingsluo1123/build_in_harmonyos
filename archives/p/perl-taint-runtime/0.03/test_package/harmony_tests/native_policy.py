"""Actual HarmonyOS unsigned-versus-signed XS loading with identical code bytes."""
import hashlib,json,os,shutil,stat,subprocess,sys,tempfile,uuid
from pathlib import Path
runtime=Path(sys.argv[1]).resolve();package=Path(sys.argv[2]).resolve();report=Path(sys.argv[3])/('harmony-taint-policy-'+uuid.uuid4().hex);report.mkdir(parents=True)
assert os.uname().sysname=='HarmonyOS' and os.uname().machine=='aarch64'
parent=Path(os.environ['TMPDIR']);assert parent.resolve()==parent and parent.stat().st_uid==os.getuid() and stat.S_IMODE(parent.stat().st_mode)==0o700
tools={n:shutil.which(n) for n in ('llvm-readelf','llvm-objcopy','binary-sign-tool')};assert all(tools.values())
clean=dict(os.environ);clean.pop('LD_LIBRARY_PATH',None);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();records=[]
def command(label,argv,env):
 p=subprocess.run(argv,env=env,capture_output=True,timeout=60)
 (report/(label+'.stdout')).write_bytes(p.stdout);(report/(label+'.stderr')).write_bytes(p.stderr)
 records.append({'label':label,'argv':argv,'rc':p.returncode,'stdout_sha256':hashlib.sha256(p.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(p.stderr).hexdigest()})
 return p
with tempfile.TemporaryDirectory(prefix='taint-ohos-policy-',dir=str(parent)) as name:
 root=Path(name);assert root.stat().st_uid==os.getuid() and stat.S_IMODE(root.stat().st_mode)==0o700
 matches=[p for p in (package/'lib/perl5/Taint/Runtime.pm',package/'lib/perl5/aarch64-linux-thread-multi/Taint/Runtime.pm') if p.is_file()];assert len(matches)==1;module=matches[0];actual=package/'lib/perl5/aarch64-linux-thread-multi/auto/Taint/Runtime/Runtime.so'
 assert module.is_file() and actual.is_file() and module.resolve().is_relative_to(package) and actual.resolve().is_relative_to(package)
 before=sha(actual);lib=root/'lib';target=lib/'auto/Taint/Runtime/Runtime.so';target.parent.mkdir(parents=True);(lib/'Taint').mkdir(exist_ok=True);shutil.copyfile(module,lib/'Taint/Runtime.pm');shutil.copyfile(actual,target);target.chmod(0o700)
 assert command('remove-private-code-signature',[tools['llvm-objcopy'],'--remove-section','.codesign',str(target)],clean).returncode==0
 assert target.stat().st_uid==os.getuid() and stat.S_IMODE(target.stat().st_mode)==0o700
 unsigned=sha(target);sections=command('unsigned-private-sections',[tools['llvm-readelf'],'-S',str(target)],clean);assert sections.returncode==0 and b'.codesign' not in sections.stdout
 env=dict(os.environ,PERL5LIB=os.pathsep.join(map(str,(lib,runtime/'lib/perl5/5.42.2',runtime/'lib/perl5/5.42.2/aarch64-linux-thread-multi'))),PERL5OPT='')
 argv=[str(runtime/'bin/perl'),'-e','use Taint::Runtime qw(taint_start taint_enabled);taint_start();die unless taint_enabled();print "HARMONY_SIGNED_XS=42\\n";']
 rejected=command('unsigned-xs-load',argv,env);assert rejected.returncode!=0 and str(target).encode() in rejected.stderr and any(message in rejected.stderr for message in (b'Operation not permitted',b'Permission denied')),'Exact private unsigned XS permission rejection required'
 signed=Path(str(target)+'.signed');assert command('sign-private-identical-xs',[tools['binary-sign-tool'],'sign','-inFile',str(target),'-outFile',str(signed),'-selfSign','1'],clean).returncode==0
 assert b'.codesign' in command('signed-private-sections',[tools['llvm-readelf'],'-S',str(signed)],clean).stdout
 signed.chmod(0o700);os.replace(signed,target);assert target.stat().st_uid==os.getuid() and stat.S_IMODE(target.stat().st_mode)==0o700;loaded=command('signed-xs-load',argv,env);assert loaded.returncode==0 and b'HARMONY_SIGNED_XS=42' in loaded.stdout
 assert sha(actual)==before,'Installed package mutated by policy test'
 result={'pass':True,'uname':list(os.uname()),'uid':os.getuid(),'mode':'0700','unsigned_elf_sha256':unsigned,'signed_elf_sha256':sha(target),'installed_xs_sha256_unchanged':before,'unsigned_owner_mode':'0700','signed_owner_mode':'0700','unsigned_load_permission_diagnostic':rejected.stderr.decode(errors='replace'),'unsigned_load_rc':rejected.returncode,'signed_load_rc':0,'records':records}
(report/'result.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print('HARMONY_TEST_COUNT=1');print('HARMONY_TEST_PASS=1/1')
