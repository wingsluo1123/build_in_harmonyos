import importlib.util,os,shlex,shutil,subprocess,sys,uuid
from pathlib import Path
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake,CMakeDeps,CMakeToolchain,cmake_layout
from conan.tools.env import VirtualRunEnv

class TestConan(ConanFile):
    settings='os','arch','compiler','build_type'
    test_type='explicit'
    def requirements(self):self.requires(self.tested_reference_str)
    def layout(self):cmake_layout(self)
    def generate(self):
        CMakeDeps(self).generate();CMakeToolchain(self).generate();VirtualRunEnv(self).generate()
    def build(self):
        cmake=CMake(self);cmake.configure();cmake.build()
        if self.settings.os=='OHOS':
            signer=shutil.which('binary-sign-tool');readelf=shutil.which('llvm-readelf');objcopy=shutil.which('llvm-objcopy')
            if not signer or not readelf or not objcopy:raise ConanInvalidConfiguration('Actual signature tool closure required')
            binary=Path(self.build_folder)/'bin/consumer';signed=Path(str(binary)+'.signed')
            clean=dict(os.environ);clean.pop('LD_LIBRARY_PATH',None)
            if b'.codesign' in subprocess.check_output([readelf,'-S',binary],env=clean):
                subprocess.run([objcopy,'--remove-section','.codesign',binary],env=clean,check=True)
            subprocess.run([signer,'sign','-inFile',binary,'-outFile',signed,'-selfSign','1'],env=clean,check=True)
            if b'.codesign' not in subprocess.check_output([readelf,'-S',signed],env=clean):raise ConanInvalidConfiguration('Signature not present')
            os.replace(signed,binary);binary.chmod(0o755)
    def test(self):
        if not can_run(self):raise ConanInvalidConfiguration('Actual target consumer execution required')
        binary=Path(self.build_folder)/'bin/consumer'
        self.run(shlex.quote(str(binary)),env='conanrun')
        if self.settings.os=='OHOS':
            dep=self.dependencies['dbus'];daemon=Path(dep.package_folder)/'bin/dbus-daemon'
            private=self.conf.get('user.dbus:private_test_root',default='',check_type=str)
            path=Path(self.source_folder)/'harmony_tests/private_socket_root.py'
            spec=importlib.util.spec_from_file_location('dbus_private_socket_root',path)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            root=module.private_test_parent(private,str(self.settings.os))
            harmony=root/('dh-'+uuid.uuid4().hex[:12])
            self.run(' '.join(shlex.quote(str(v)) for v in [sys.executable,Path(self.source_folder)/'harmony_tests/numeric_external.py',binary,daemon,harmony]),env='conanrun')
