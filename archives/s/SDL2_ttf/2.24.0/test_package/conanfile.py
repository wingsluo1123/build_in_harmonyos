#!/usr/bin/env python3
"""Conan test_package — SDL2_ttf 2.24.0

L1 test: verify the package can be found and linked.
Uses direct compilation to keep test simple.
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
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
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compiler_executables.get("c")
        if not cc:
            raise ConanInvalidConfiguration(
                "tools.build:compiler_executables.c is required to build the consumer"
            )
        source = os.path.join(self.source_folder, "test_sdl2_ttf.c")
        self.run(
            f"{shlex.quote(cc)} {shlex.quote(source)} -o test_sdl2_ttf "
            f"{inc_flags} {lib_flags} {link_flags} {system_flags}"
        )

    def test(self):
        if can_run(self):
            self.run("./test_sdl2_ttf", env="conanrun")
