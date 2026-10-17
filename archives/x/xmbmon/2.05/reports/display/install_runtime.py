#!/usr/bin/env python3
"""Build a task-local Xvfb runtime from the pinned deployment bundle on HarmonyOS."""
import argparse,hashlib,json,os,pathlib,shutil,subprocess,tarfile

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--work',type=pathlib.Path,required=True,help='new task-private directory; display must not exist')
 p.add_argument('--graph',type=pathlib.Path,required=True,help='successful native conan create JSON graph')
 p.add_argument('--sdk',type=pathlib.Path,default=pathlib.Path('/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native'))
 a=p.parse_args();b=pathlib.Path(__file__).resolve().parent;w=a.work.resolve()
 for row in json.loads((b/'MANIFEST.json').read_text())['files']:
  f=b/row['path']
  if hashlib.sha256(f.read_bytes()).hexdigest()!=row['sha256']:raise RuntimeError('Hash mismatch: '+str(f))
 d=w/'display';d.mkdir(parents=True,exist_ok=False)
 temp=w/'tmp';temp.mkdir(exist_ok=True)
 for archive in sorted((b/'archives').glob('*.tar.gz')):
  with tarfile.open(archive) as t:t.extractall(d,filter='data')
 (d/'lib/libpixman-1.so.0').symlink_to('libpixman-1.so.0.46.4')
 (d/'fb').mkdir()
 with tarfile.open(b/'sources/libxkbfile-1.1.3.tar.xz') as t:t.extractall(w/'display-src',filter='data')
 src=w/'display-src/libxkbfile-1.1.3'
 graph=json.loads(a.graph.read_text());folders=[pathlib.Path(n['package_folder']) for n in graph['graph']['nodes'].values() if n.get('package_folder')]
 env=dict(os.environ,TMPDIR=str(temp),LD_LIBRARY_PATH=str(a.sdk/'llvm/lib')+':'+os.environ.get('LD_LIBRARY_PATH',''))
 cc=[str(a.sdk/'llvm/bin/clang'),'--target=aarch64-linux-ohos','--sysroot='+str(a.sdk/'sysroot')]
 subprocess._USE_POSIX_SPAWN=False
 records=[]
 def run(name,args):
  r=subprocess.run(args,env=env,capture_output=True,text=True,timeout=120)
  records.append({'name':name,'command':args,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
  (w/'display-install.json').write_text(json.dumps(records,indent=2)+'\n')
  print(name,r.returncode,flush=True)
  if r.returncode:raise RuntimeError(r.stdout+r.stderr)
 run('libpng shared from official static archive',cc+['-shared','-Wl,-Bsymbolic,-soname,libpng16.so.16','-o',str(d/'lib/libpng16.so.16'),'-Wl,--whole-archive',str(d/'lib/liblibpng16_static.a'),str(d/'lib/libz.a'),'-Wl,--no-whole-archive','-lm'])
 run('libxkbfile from upstream 1.1.3',cc+['-shared','-O2','-fPIC','-Wl,-soname,libxkbfile.so.1','-o',str(d/'lib/libxkbfile.so.1'),'-I'+str(src/'include'),'-I'+str(src/'include/X11/extensions')]+['-I'+str(f/'include') for f in folders]+list(map(str,(src/'src').glob('*.c')))+['-L'+str(f/'lib') for f in folders]+['-lX11'])
 run('Xvfb process-local path and loopback adapter',cc+['-shared','-O2','-fPIC',str(b/'xvfb_local_paths.c'),'-o',str(d/'lib/xvfb_local_paths.so'),'-ldl'])
 env['LD_LIBRARY_PATH']=str(d/'lib')+':'+':'.join(str(f/'lib') for f in folders)+':'+env['LD_LIBRARY_PATH']
 for name in ('Xvfb','xkbcomp'):run(name+' loader check',[str(d/'bin'/name),'-help'])
 print('Runtime ready at',d)

if __name__=='__main__':main()
