#!/usr/bin/env python3
"""Conan test_package — ncurses 6.5."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class NcursesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        cc = executables.get("c", "cc")

        dep = self.dependencies["ncurses"]
        include_flags = " ".join(f'-I"{path}"' for path in dep.cpp_info.includedirs)
        extra_cflags = " ".join(dep.cpp_info.cflags)
        libdir_flags = " ".join(f'-L"{path}"' for path in dep.cpp_info.libdirs)
        libs = " ".join(f"-l{lib}" for lib in dep.cpp_info.libs)

        self.run(
            f'{cc} {include_flags} {extra_cflags} test.c '
            f'{libdir_flags} {libs} -o test_ncurses'
        )

    def test(self):
        if can_run(self):
            self.run(
                os.path.join(self.build_folder, "test_ncurses"),
                env="conanrun",
            )
