#!/usr/bin/env python3
"""Conan test_package for spim — verifies the spim binary works.

Runs a simple MIPS assembly program through spim and checks the exit code.
"""
import os

from conan import ConanFile
from conan.tools.files import copy


class SpimTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # Get the spim binary and exceptions.s paths
        spim_pkg = self.dependencies["spim"]
        spim_bin = os.path.join(spim_pkg.cpp_info.bindirs[0], "spim")
        exc_path = os.path.join(spim_pkg.cpp_info.resdirs[0], "exceptions.s")

        # Run a simple MIPS assembly program through spim
        test_asm = os.path.join(self.source_folder, "test_hello.s")
        self.run(f'"{spim_bin}" -ef "{exc_path}" -file "{test_asm}"', env="conanrun")
