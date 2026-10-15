#!/usr/bin/env python3
"""Conan test_package for spaln 3.0.7.

Builds an OHOS aarch64 consumer program (test_spaln.c) that runs the packaged
``spaln`` / ``sortgrcd`` / ``makdbs`` / ``makmdm`` executables and asserts on
their observable behaviour, then executes it on the target.
"""
import os
import platform

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class SpalnTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        configured = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = configured.get("cpp") or configured.get("c")
        build_env = Environment()
        if compiler:
            # The OHOS SDK lld resolves libxml2 from the toolchain's own lib dir.
            toolchain_lib = os.path.realpath(
                os.path.join(os.path.dirname(compiler), os.pardir, "lib")
            )
            if os.path.isdir(toolchain_lib):
                build_env.prepend_path("LD_LIBRARY_PATH", toolchain_lib)
        with build_env.vars(self).apply():
            cmake.configure()
            cmake.build()

    def test(self):
        bindir = self.dependencies["spaln"].cpp_info.bindirs[0]
        spaln_bin = os.path.join(bindir, "spaln")
        machine = platform.machine().lower()

        if not (machine.startswith("aarch") or machine.startswith("arm")):
            # Honest deferral, not a silent skip: this box is running the
            # cross-build, so the aarch64/OHOS consumer binary cannot be
            # executed here.  It is executed on the OHOS worker.
            self.output.info(
                f"build host machine={machine}: deferring execution of the "
                f"cross-compiled OHOS consumer test to the aarch64 worker"
            )
            return

        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_spaln")
        self.run(f'"{test_bin}" "{spaln_bin}"', env="conanrun")
