#!/usr/bin/env python3
"""Conan recipe for CUnit 2.1-3 — Custom build system.

CUnit is a simple unit testing framework for C.
Build: Custom Makefile (autotools fails on OHOS due to temp file permissions).
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CUnitConan(ConanFile):
    name = "cunit"
    version = "2.1-3"
    description = "CUnit is a system for writing, administering, and running unit tests in C."
    license = "BSD-3-Clause"
    homepage = "http://cunit.sourceforge.net/"
    url = ""

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            raise ConanInvalidConfiguration("cunit does not support shared builds")

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"

        source_dir = self.source_folder
        build_dir = self.build_folder

        include_dir = os.path.join(build_dir, "include")
        os.makedirs(include_dir, exist_ok=True)

        self.run(f"{cc} -E -P -DVERSION=\\\"2.1\\\" -DRELEASE=\\\"3\\\" "
                 f"{source_dir}/CUnit/CUnit.h.in > {include_dir}/CUnit.h")

        headers = [
            "CUnit/TestDB.h", "CUnit/TestRun.h", "CUnit/Basic.h",
            "CUnit/Automated.h", "CUnit/Console.h", "CUnit/CI.h",
        ]
        for h in headers:
            src = os.path.join(source_dir, h)
            dst = os.path.join(build_dir, h)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            self.run(f"cp {src} {dst}")

        src_files = [
            "CUnit/CUError.c", "CUnit/CUList.c", "CUnit/CUMemory.c",
            "CUnit/CURegistry.c", "CUnit/CUTest.c", "CUnit/CUUtil.c",
            "CUnit/TestRun.c", "CUnit/Basic.c", "CUnit/Automated.c",
            "CUnit/Console.c", "CUnit/CI.c",
        ]

        objects = []
        for src in src_files:
            obj = os.path.join(build_dir, src.replace(".c", ".o"))
            os.makedirs(os.path.dirname(obj), exist_ok=True)
            self.run(f"{cc} -c {source_dir}/{src} -o {obj} -I{include_dir} -fPIC")
            objects.append(obj)

        ar = compilers.get("ar", "llvm-ar") if compilers else "llvm-ar"
        lib_path = os.path.join(build_dir, "libcunit.a")
        self.run(f"{ar} rcs {lib_path} {' '.join(objects)}")

    def package(self):
        self.copy("*.h", dst="include", src=self.build_folder)
        self.copy("libcunit.a", dst="lib", src=self.build_folder)

    def package_info(self):
        self.cpp_info.libs = ["cunit"]