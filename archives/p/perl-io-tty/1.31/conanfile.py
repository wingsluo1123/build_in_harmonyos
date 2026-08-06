#!/usr/bin/env python3
"""Conan recipe — perl-io-tty 1.31 (auto-generated for Perl 5.42.2 rebuild)"""
import os, shutil
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches

class PerlIoTty(ConanFile):
    name = "perl-io-tty"
    version = "1.31"
    description = "perl-io-tty 1.31"
    license = "Artistic-2.0"
    homepage = "https://metacpan.org/pod/io::tty"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):

        src = self.source_folder
        apply_conandata_patches(self)
        self.run("perl Makefile.PL", cwd=src)
        # HarmonyOS: patch Makefile for CRT linker flags (R32: OHOS-only)
        if self.settings.os == "OHOS":
            makefile = os.path.join(src, "Makefile")
            if os.path.exists(makefile):
                with open(makefile, "r") as mf:
                    content = mf.read()
                if "-nostartfiles" not in content:
                    content = content.replace("LDDLFLAGS =", "LDDLFLAGS = -nostartfiles -nodefaultlibs -L/system/lib64 -lc")
                with open(makefile, "w") as mf:
                    mf.write(content)
        self.run("make -j1", cwd=src)

    def package(self):
        dest = self.package_folder
        src = self.source_folder
        self.run("make install DESTDIR=" + dest, cwd=src)

        for root, dirs, files in os.walk(dest):
            for fn in files:
                if fn.endswith(".so"):
                    lib_dir = os.path.join(dest, "lib")
                    os.makedirs(lib_dir, exist_ok=True)
                    shutil.copy2(os.path.join(root, fn), lib_dir)

    def package_info(self):
        # The shared library is Tty.so (Perl XS extension)
        self.cpp_info.libs = ["Tty"]
        self.cpp_info.libdirs = ["lib"]
        # Perl module path for consumers
        self.cpp_info.includedirs = []
