#!/usr/bin/env python3
"""Conan test_package — SDL2_ttf 2.24.0

L1 test: verify the package can be found and linked.
Uses direct compilation to keep test simple.
"""
import os

from conan import ConanFile


class Sdl2TtfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["sdl2_ttf"]
        cpp = dep.cpp_info
        inc_flags = " ".join(f"-I{d}" for d in cpp.includedirs)
        lib_flags = " ".join(f"-L{d}" for d in cpp.libdirs)
        link_flags = " ".join(f"-l{l}" for l in cpp.libs)
        cc = os.environ.get("CC", "clang")
        self.run(f"{cc} test_sdl2_ttf.c -o test_sdl2_ttf {inc_flags} {lib_flags} {link_flags}")

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_sdl2_ttf'", env="conanrun")
