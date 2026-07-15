#!/usr/bin/env python3
"""Conan test_package — tass64 1.60.3243

Tests the 64tass binary by running --version and assembling a
simple 6502 program. tass64 is a command-line tool, not a library.
"""
import os

from conan import ConanFile


class Tass64TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # No build step needed for a binary tool

    def test(self):
        # Get the bin path from the dependency's package
        bin_dir = self.dependencies["tass64"].cpp_info.bindirs[0]
        tass64_bin = os.path.join(bin_dir, "64tass")
        # Run 64tass --version to verify the binary works
        self.run(f'"{tass64_bin}" --version', env="conanrun")
        # Assemble a test program (R34: test must actually use the package)
        test_asm = os.path.join(self.source_folder, "test.asm")
        output_prg = os.path.join(self.build_folder, "test.prg")
        self.run(f'"{tass64_bin}" "{test_asm}" -o "{output_prg}"', env="conanrun")
