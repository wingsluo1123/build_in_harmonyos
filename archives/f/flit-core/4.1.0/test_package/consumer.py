import hashlib,importlib.util,json,os,sys,tarfile,tempfile
from pathlib import Path
from zipfile import ZipFile
from backend_fixture import *
import flit_core
from flit_core import buildapi
package=Path(sys.argv[1]).resolve();assert flit_core.__version__=='4.1.0' and Path(flit_core.__file__).resolve().is_relative_to(package/'lib/python3.12/site-packages')
with tempfile.TemporaryDirectory(prefix='flit-consumer-',dir=private_parent()) as value:
    root=Path(value);assert_private(root);source=fixture(root/'source');out=root/'dist';out.mkdir()
    with cwd(source):
        assert buildapi.get_requires_for_build_wheel()==[]
        wheel=out/buildapi.build_wheel(str(out));digest=audit_wheel(wheel)
        installed=root/'installed';installed.mkdir()
        with ZipFile(wheel) as z:z.extractall(installed)
        spec=importlib.util.spec_from_file_location('ohpc_flit_probe',installed/'ohpc_flit_probe/__init__.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);assert module.value==42 and Path(module.__file__).resolve().is_relative_to(installed)
        assert (installed/'ohpc_flit_probe/data.bin').read_bytes()==PAYLOAD
        print('CONSUMER_WHEEL_RECORD_AND_INSTALLED_API=PASS')
        sdist=out/buildapi.build_sdist(str(out))
        with tarfile.open(sdist) as tf:
            members=tf.getmembers();assert all(not p.issym() and not p.islnk() and not Path(p.name).is_absolute() and '..' not in Path(p.name).parts for p in members)
            assert tf.extractfile('ohpc_flit_probe-0.1/ohpc_flit_probe/data.bin').read()==PAYLOAD
            assert tf.extractfile('ohpc_flit_probe-0.1/ohpc_flit_probe/__init__.py').read()==MODULE
        print('CONSUMER_SDIST_REAL_SOURCE=PASS')
        editable=root/'editable';editable.mkdir();name=buildapi.build_editable(str(editable))
        with ZipFile(editable/name) as z:
            assert z.read('ohpc_flit_probe.pth').decode()==str(source.resolve());assert b'Name: ohpc_flit_probe\n' in z.read('ohpc_flit_probe-0.1.dist-info/METADATA')
        print('CONSUMER_PEP660_ACTUAL_SOURCE_PATH=PASS')
    (Path.cwd()/'consumer-results.json').write_text(json.dumps({'consumer_pass':3,'wheel_sha256':digest,'backend_file':flit_core.__file__,'backend_sha256':hashlib.sha256(Path(flit_core.__file__).read_bytes()).hexdigest(),'installed_api':42},indent=2))
print('CONSUMER_TEST_PASS=3/3')
