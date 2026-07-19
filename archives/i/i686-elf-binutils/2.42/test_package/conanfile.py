#!/usr/bin/env python3
"""Conan test_package for i686-elf-binutils 2.42.

R34: Test must substantively depend on the tested package.
Runs i686-elf-as/ld/objdump/readelf --version to verify the cross-binutils work.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class I686ElfBinutilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Run actual tool binaries to verify the package works
        bindir = self.dependencies["i686-elf-binutils"].cpp_info.bindirs[0]
        for tool in ["i686-elf-as", "i686-elf-ld", "i686-elf-objdump", "i686-elf-readelf"]:
            self.run(f"{os.path.join(bindir, tool)} --version", env="conanrun")
