#!/usr/bin/env python3
"""Conan test_package — SDL2_ttf 2.24.0

L1 test: verify the package can be found and linked.
Uses direct compilation to keep test simple.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


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
        system_flags = " ".join(f"-l{l}" for l in cpp.system_libs)
        cc = os.environ.get("CC", "clang")
        self.run(
            f"{cc} test_sdl2_ttf.c -o test_sdl2_ttf "
            f"{inc_flags} {lib_flags} {link_flags} {system_flags}"
        )

    def test(self):
        if can_run(self):
            self.run("./test_sdl2_ttf", env="conanrun")
