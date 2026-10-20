#!/usr/bin/env python3
"""Conan test_package for pgagroal 2.1.0."""
import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class PgagroalTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # Serial build, like the recipe: OHOS CI workers fail to fork under load
        # and CMake's feature probes silently answer "no" when they cannot fork.
        # `cli_args=["-j1"]` would not do it, Conan appends `-- -j<jobs>`.
        self.conf.define("tools.build:jobs", 1)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("Cross-compiling without an emulator: skipping the execution test")
            return
        dep = self.dependencies["pgagroal"]
        bindir = dep.cpp_info.bindirs[0] if dep.cpp_info.bindirs else "bin"
        if not os.path.isabs(bindir):
            bindir = os.path.join(dep.package_folder, bindir)
        # libpgagroal.so keeps its dependencies as separate shared objects (zstd),
        # so every package of the graph contributes its libdir to the loader path.
        libdirs = []
        for dependency in self.dependencies.host.values():
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                libdirs.append(libdir)
        env = {
            "PATH": bindir + os.pathsep + os.environ.get("PATH", ""),
            "LD_LIBRARY_PATH": os.pathsep.join(
                libdirs + [os.environ.get("LD_LIBRARY_PATH", "")]).strip(os.pathsep),
        }
        prefix = " ".join(f"{k}={shlex.quote(v)}" for k, v in env.items())
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_pgagroal")
        self.run(f"{prefix} {shlex.quote(bin_path)}", env="conanrun")
