#!/usr/bin/env python3
"""Conan recipe — perl-json-xs 4.04 (auto-generated for Perl 5.42.2 rebuild)"""
import os, shutil
from conan import ConanFile
from conan.tools.files import get

class PerlJsonXs(ConanFile):
    name = "perl-json-xs"
    version = "4.04"
    description = "perl-json-xs 4.04"
    license = "Artistic-2.0"
    homepage = "https://metacpan.org/pod/json::xs"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):

        src = self.source_folder
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
                    # Rename to avoid conflict with other XS.so packages
                    target = os.path.join(lib_dir, "JSON_XS.so")
                    shutil.copy2(os.path.join(root, fn), target)

    def package_info(self):
        # Renamed from XS to JSON_XS to avoid .so naming conflict
        self.cpp_info.libs = ["JSON_XS"]
        self.cpp_info.libdirs = ["lib"]
        # Perl module path for consumers
        self.cpp_info.includedirs = []
