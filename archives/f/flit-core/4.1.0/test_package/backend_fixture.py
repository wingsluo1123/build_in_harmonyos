import base64,csv,hashlib,io,os,stat
from pathlib import Path
from zipfile import ZipFile
PAYLOAD=bytes(range(256))+b'\x00HarmonyOS\xff\r\n'
MODULE=b'"""Actual installed backend consumer fixture."""\n__version__="0.1"\nvalue=42\n'
PROJECT='[build-system]\nrequires=["flit_core>=3.11,<5"]\nbuild-backend="flit_core.buildapi"\n[project]\nname="ohpc_flit_probe"\nversion="0.1"\ndescription="Actual backend fixture"\n'
def fixture(root):
    root.mkdir();(root/'ohpc_flit_probe').mkdir();(root/'ohpc_flit_probe/__init__.py').write_bytes(MODULE);(root/'ohpc_flit_probe/data.bin').write_bytes(PAYLOAD);(root/'pyproject.toml').write_text(PROJECT)
    return root
class cwd:
    def __init__(self,p):self.p=p
    def __enter__(self):self.old=Path.cwd();os.chdir(self.p)
    def __exit__(self,*args):os.chdir(self.old)
def audit_wheel(path):
    with ZipFile(path) as z:
        names=z.namelist();assert len(names)==len(set(names)) and all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in names)
        assert z.read('ohpc_flit_probe/__init__.py')==MODULE and z.read('ohpc_flit_probe/data.bin')==PAYLOAD
        rows=list(csv.reader(io.StringIO(z.read('ohpc_flit_probe-0.1.dist-info/RECORD').decode())))
        assert {r[0] for r in rows}==set(names)
        for n,h,size in rows:
            if n.endswith('/RECORD'):assert h==size=='';continue
            data=z.read(n);assert int(size)==len(data) and h=='sha256='+base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip('=')
        assert b'Name: ohpc_flit_probe\n' in z.read('ohpc_flit_probe-0.1.dist-info/METADATA')
    return hashlib.sha256(path.read_bytes()).hexdigest()
def private_parent():
    for s in (os.environ.get('TMPDIR'),'/data/storage/el2/base/cache'):
        if not s:continue
        p=Path(s)
        if p.is_absolute() and p.is_dir() and p.resolve()==p and not p.is_symlink() and p.stat().st_uid==os.getuid() and os.access(p,os.W_OK|os.X_OK):return p
    raise RuntimeError('Real owned POSIX parent missing')
def assert_private(p):assert p.resolve()==p and not p.is_symlink() and p.stat().st_uid==os.getuid() and stat.S_IMODE(p.stat().st_mode)==0o700
