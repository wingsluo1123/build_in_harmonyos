#!/usr/bin/env python3
"""Conan recipe — perl-math-random-mt-auto 6.23-r10 (auto-generated for Perl 5.42.2 rebuild)"""
import os, shutil
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches

class PerlMathRandomMtAuto(ConanFile):
    name = "perl-math-random-mt-auto"
    version = "6.23-r10"
    description = "perl-math-random-mt-auto 6.23-r10"
    license = "Artistic-2.0"
    homepage = "https://metacpan.org/pod/math::random::mt::auto"
    settings = "os", "compiler", "build_type", "arch"
    def export_sources(self):
        export_conandata_patches(self)

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
        # The shared library is Auto.so (Perl XS extension)
        self.cpp_info.libs = ["Auto"]
        self.cpp_info.libdirs = ["lib"]
        # Perl module path for consumers
        self.cpp_info.includedirs = []
