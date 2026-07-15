#!/usr/bin/env python3
"""Conan test_package - cdk 5.0 (L1 official test).

Verifies the CDK header (cdk.h) is available and the package can be consumed.
CI runs this automatically via `conan create` (which invokes test_package).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class CdkTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        src = os.path.join(self.source_folder, "test_package.c")
        inc = [f"-I{p}" for p in self.deps_cpp_info.include_paths]
        libdirs = [f"-L{p}" for p in self.deps_cpp_info.lib_paths]
        libs = [f"-l{l}" for l in self.deps_cpp_info.libs]
        self.run(f"cc {' '.join(inc)} {src} {' '.join(libdirs)} {' '.join(libs)} -o test_package")

    def test(self):
        if can_run(self):
            cmd = os.path.join(self.build_folder, "test_package")
            self.run(cmd, env="conanrun")
