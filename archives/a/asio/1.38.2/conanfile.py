import os
from pathlib import Path
import shlex
import shutil
import sys
from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

COMPILER = r'''
from pathlib import Path
import os, shutil, subprocess, sys
root=Path(sys.argv[1]).resolve(strict=True)
compiler=sys.argv[2]; args=sys.argv[3:]
resolved=shutil.which(compiler)
if not resolved: raise RuntimeError('configured compiler missing')
with open(resolved,'rb') as stream: script=stream.read(2)==b'#!'
shell=shutil.which('sh')
if script and not shell: raise RuntimeError('compiler script requires sh')
command=[shell,resolved,*args] if script else [resolved,*args]
rc=subprocess.run(command,check=False).returncode
if rc: raise SystemExit(rc)
if any(flag in args for flag in ('-c','-E','-S')): raise SystemExit(0)
if not any(Path(arg).suffix in ('.c','.cc','.cpp','.cxx','.o','.lo','.s','.S','.a') for arg in args): raise SystemExit(0)
output=args[args.index('-o')+1] if '-o' in args else 'a.out'
if output=='-': raise SystemExit(0)
p=Path(output).absolute(); p.relative_to(root)
for ancestor in (p,*p.parents):
 if ancestor.is_symlink(): raise RuntimeError('redirected compiler output')
if not p.is_file(): raise RuntimeError('linked output absent')
with p.open('rb') as stream: header=stream.read(20)
if header[:4]!=b'\x7fELF' or int.from_bytes(header[16:18],'little') not in (2,3): raise SystemExit(0)
signed=p.with_name(p.name+'.signed')
if signed.exists(): raise RuntimeError('signature output already exists')
signer=shutil.which('binary-sign-tool'); readelf=shutil.which('llvm-readelf')
if not signer or not readelf: raise RuntimeError('signing tools missing')
r=subprocess.run([signer,'sign','-inFile',str(p),'-outFile',str(signed),'-selfSign','1'],capture_output=True)
if r.returncode:
 sys.stderr.buffer.write(r.stdout+r.stderr);raise SystemExit(r.returncode)
sections=subprocess.run([readelf,'-S',str(signed)],capture_output=True,check=True).stdout
if b'.codesign' not in sections: raise RuntimeError('signed ELF has no codesign section')
signed.chmod(p.stat().st_mode); signed.replace(p)
'''

class AsioConan(ConanFile):
    name = "asio"
    version = "1.38.2"
    license = "BSL-1.0"
    description = "Standalone C++ asynchronous I/O and networking"
    homepage = "https://think-async.com/Asio/"
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "upstream.py"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("Native Linux/OHOS validation only")
        if cross_building(self):
            raise ConanInvalidConfiguration("Full upstream tests require native execution")
        if str(self.settings.compiler.cppstd).replace("gnu", "") != "17":
            raise ConanInvalidConfiguration("This validated standalone test configuration uses C++17")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        export_conandata_patches(self)

    def generate(self):
        (Path(self.build_folder) / "signed-compiler.py").write_text(COMPILER, encoding="utf-8")

    def build(self):
        apply_conandata_patches(self)
        executables = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        compiler = shutil.which(executables.get("cpp", "clang++"))
        if not compiler:
            raise ConanException("Configured C++ compiler missing")
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration("Current signing-aware upstream runner is validated for native OHOS")
        self.run(shlex.join([sys.executable, str(Path(self.source_folder) / "upstream.py"),
                             self.source_folder, str(Path(self.build_folder) / "upstream"),
                             str(Path(self.build_folder) / "signed-compiler.py"), compiler, "17"]),
                 env="conanbuild")

    def package(self):
        copy(self, "*.hpp", str(Path(self.source_folder) / "include"), str(Path(self.package_folder) / "include"))
        copy(self, "*.ipp", str(Path(self.source_folder) / "include"), str(Path(self.package_folder) / "include"))
        copy(self, "LICENSE_1_0.txt", self.source_folder, str(Path(self.package_folder) / "licenses"))

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "asio")
        self.cpp_info.set_property("cmake_target_name", "asio::asio")
        self.cpp_info.set_property("pkg_config_name", "asio")
        self.cpp_info.defines = ["ASIO_STANDALONE"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
