#!/usr/bin/env python3
"""Conan test_package for libgd 2.3.3 -- consumer L1 test.

Compiles a small C program that #includes <gd.h>, then dlopen()s
libgd.so at runtime and calls gdImageCreate/gdImageDestroy to verify
the shared library loads and the public API is callable.
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["libgd"].cpp_info
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)
        libdir = dep.libdirs[0]
        so = os.path.join(libdir, "libgd.so")
        cc = os.environ.get("CC", "clang")
        self.run(
            f'{cc} test.c -o test_probe {inc} '
            f'-DTARGET_SO=\'"{so}"\' -ldl'
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: only compile+link verified")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")
