import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
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


class LibplistConan(ConanFile):
    name = "libplist"
    version = "2.8.0"
    license = "LGPL-2.1-or-later"
    description = "C/C++ Apple property list parser, writer and plistutil utility"
    homepage = "https://github.com/libimobiledevice/libplist"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("Linux/OHOS only")
        if cross_building(self):
            raise ConanInvalidConfiguration("The complete upstream suite requires native execution")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        export_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc._build = tc._host = tc._target = None
        tc.configure_args.extend(["--without-cython", "--with-tools", "--with-tests"])
        tc.generate()
        root = Path(self.build_folder)
        env = tc.environment()
        compiler = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        if self.settings.os == "OHOS":
            launcher = root / "signed-compiler.py"
            launcher.write_text(COMPILER, encoding="utf-8")
            resolved = shutil.which(compiler.get("c", "clang"))
            shell = shutil.which("sh")
            if not resolved or not shell:
                raise ConanException("Configured compiler/shell not found")
            with open(resolved, "rb") as stream:
                script = stream.read(2) == b"#!"
            command = [shell, resolved] if script else [resolved]
            triplet = subprocess.run(command + ["-dumpmachine"], capture_output=True, text=True, check=True).stdout.strip()
            if not triplet.startswith("aarch64-") or not triplet.endswith("ohos"):
                raise ConanException("Expected native OHOS aarch64 compiler")
            env.define("ac_cv_build", triplet)
            for variable, key, default in (("CC", "c", "clang"), ("CXX", "cpp", "clang++")):
                tool = shutil.which(compiler.get(key, default))
                if not tool:
                    raise ConanException("Configured compiler missing")
                env.define(variable, shlex.join([sys.executable, str(launcher), str(root), tool]))
            wrappers = root / "configure-tools"
            wrappers.mkdir(exist_ok=True)
            wrapper = wrappers / "mktemp"
            wrapper.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            wrapper.chmod(0o755)
            env.prepend_path("PATH", str(wrappers))
            env.define("CONFIG_SHELL", shell)
            env.define("SHELL", shell)
        temp = root / "test-tmp"
        temp.mkdir(exist_ok=True)
        env.define("TMPDIR", str(temp))
        env.prepend_path("LD_LIBRARY_PATH", str(root / "src/.libs"))
        env.vars(self).save_script("conanbuildenv")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        autotools.make(target="check", args=["-j1"])
        source = Path(self.source_folder) / "test/Makefile.am"
        import re
        block = source.read_text().split("TESTS =", 1)[1].split("EXTRA_DIST", 1)[0]
        names = re.findall(r"[a-zA-Z0-9_+.-]+[.]test", block)
        if len(names) != 43 or len(set(names)) != 43:
            raise ConanException("Upstream test inventory changed")
        for name in names:
            result = (Path(self.build_folder) / "test" / (name.removesuffix(".test") + ".trs")).read_text()
            if result.splitlines().count(":test-result: PASS") != 1:
                raise ConanException("Upstream test did not pass: " + name)
        self.output.info("UPSTREAM_N_OF_N_PASS 43 (43/43 Automake tests)")

    def package(self):
        Autotools(self).install()
        copy(self, "COPYING*", self.source_folder, os.path.join(self.package_folder, "licenses"))
        for path in (Path(self.package_folder) / "lib").glob("*.la"):
            path.unlink()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libplist-2.0")
        self.cpp_info.set_property("cmake_target_name", "libplist::libplist")
        self.cpp_info.components["core"].libs = ["plist-2.0"]
        self.cpp_info.components["core"].set_property("cmake_target_name", "libplist::core")
        self.cpp_info.components["core"].system_libs = ["m"]
        self.cpp_info.components["core"].set_property("pkg_config_name", "libplist-2.0")
        self.cpp_info.components["cpp"].libs = ["plist++-2.0"]
        self.cpp_info.components["cpp"].set_property("cmake_target_name", "libplist::cpp")
        self.cpp_info.components["cpp"].requires = ["core"]
        self.cpp_info.components["cpp"].set_property("pkg_config_name", "libplist++-2.0")
        self.cpp_info.bindirs = ["bin"]
