#!/usr/bin/env python3
"""Conan test_package for libblockdev 3.4.0 — L1 official test.

Verifies that the libblockdev package provides a functional API by calling
bd_loop_init() and bd_loop_close() — the loop plugin is the only plugin
enabled on HarmonyOS.
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building


class LibblockdevTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps", "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Collect include and lib paths from all dependencies (including components)
        inc_dirs = set()
        lib_dirs = set()
        libs = []

        for dep_name, dep in self.dependencies.items():
            cpp_info = dep.cpp_info
            # Top-level include dirs
            for incdir in cpp_info.includedirs:
                inc_dirs.add(f"-I{incdir}")
            # Component include dirs (e.g. glib's include/glib-2.0)
            for comp_name, comp in cpp_info.components.items():
                for incdir in comp.includedirs:
                    inc_dirs.add(f"-I{incdir}")
                for lib in comp.libs:
                    p = f"-l{lib}"
                    if p not in libs:
                        libs.append(p)
                for libdir in comp.libdirs:
                    lib_dirs.add(f"-L{libdir}")
            # Top-level libs
            for lib in cpp_info.libs:
                p = f"-l{lib}"
                if p not in libs:
                    libs.append(p)
            for libdir in cpp_info.libdirs:
                lib_dirs.add(f"-L{libdir}")

        cflags = " ".join(sorted(inc_dirs))
        ldflags = " ".join(sorted(lib_dirs)) + " " + " ".join(libs)

        compiler = "clang"
        self.run(f"{compiler} {cflags} -o test_libblockdev test.c {ldflags} -ldl -lpthread -lm",
                 env="conanbuild")

    def test(self):
        if cross_building(self):
            self.output.warning("Skipping test (cross-building)")
            return
        test_bin = os.path.join(self.build_folder, "test_libblockdev")
        self.run(test_bin, env="conanrun")
