#!/usr/bin/env python3
"""Conan test_package for i686-elf-gcc 13.3.0.

R34: Test must substantively depend on the tested package.
Runs i686-elf-gcc --version and i686-elf-g++ --version to verify
the cross-compiler binaries work.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class I686ElfGccTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Run actual tool binaries to verify the package works
        bindir = self.dependencies["i686-elf-gcc"].cpp_info.bindirs[0]
        self.run(f"{os.path.join(bindir, 'i686-elf-gcc')} --version", env="conanrun")
        self.run(f"{os.path.join(bindir, 'i686-elf-g++')} --version", env="conanrun")
