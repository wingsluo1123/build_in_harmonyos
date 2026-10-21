"""Actual HMDFS owner projection to owned POSIX backend output, compared to POSIX source."""
import hashlib,json,os,sys,tempfile
from pathlib import Path
from backend_fixture import *
import flit_core
from flit_core import buildapi
assert os.uname().sysname=='HarmonyOS' and os.uname().machine=='aarch64'
package=Path(sys.argv[1]).resolve();assert Path(flit_core.__file__).resolve().is_relative_to(package/'lib/python3.12/site-packages')
parent=Path('/storage/Users/currentUser/.cache');assert parent.is_dir() and parent.resolve()==parent and not parent.is_symlink();uid=os.getuid();assert parent.stat().st_uid!=uid
old=os.environ.get('SOURCE_DATE_EPOCH');os.environ['SOURCE_DATE_EPOCH']='1700000000'
try:
    with tempfile.TemporaryDirectory(prefix='flit-hmdfs-',dir=parent) as mapped_value,tempfile.TemporaryDirectory(prefix='flit-posix-',dir=private_parent()) as private_value:
        mapped=Path(mapped_value);private=Path(private_value);assert_private(private)
        assert mapped.resolve()==mapped and not mapped.is_symlink() and mapped.stat().st_uid==parent.stat().st_uid!=uid
        a=fixture(mapped/'source');b=fixture(private/'source');out_a=private/'mapped-output';out_b=private/'posix-output';out_a.mkdir();out_b.mkdir()
        assert (a/'ohpc_flit_probe/data.bin').stat().st_uid!=uid and (b/'ohpc_flit_probe/data.bin').stat().st_uid==uid
        with cwd(a):wa=out_a/buildapi.build_wheel(str(out_a))
        with cwd(b):wb=out_b/buildapi.build_wheel(str(out_b))
        da=audit_wheel(wa);db=audit_wheel(wb);assert da==db and wa.stat().st_uid==wb.stat().st_uid==uid
        record={'pass':True,'uname':list(os.uname()),'uid':uid,'mapped_uid':mapped.stat().st_uid,'mapped_parent_uid':parent.stat().st_uid,'private_uid':private.stat().st_uid,'private_mode':oct(private.stat().st_mode&0o777),'mapped_wheel_sha256':da,'posix_wheel_sha256':db,'source_payload_sha256':hashlib.sha256(PAYLOAD).hexdigest(),'backend_file':flit_core.__file__}
        (Path.cwd()/'harmony-results.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
finally:
    if old is None:os.environ.pop('SOURCE_DATE_EPOCH',None)
    else:os.environ['SOURCE_DATE_EPOCH']=old
print('HARMONY_TEST_PASS=1/1')
