#!/usr/bin/env python3
"""Conan test_package for i686-elf-grub 2.12.

R34: Test must substantively depend on the tested package.
Runs grub-mkimage --version to verify the GRUB tools work.
"""
import os
from conan import ConanFile

class I686ElfGrubTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bindir = self.dependencies["i686-elf-grub"].cpp_info.bindirs[0]
        self.run(f"{os.path.join(bindir, 'grub-mkimage')} --version", env="conanrun")
