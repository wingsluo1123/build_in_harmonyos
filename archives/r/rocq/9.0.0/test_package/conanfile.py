#!/usr/bin/env python3
"""Conan test_package -- Rocq 9.0.0

Verifies that rocq is installed and can compile proof files.
Test: compile test_rocq.v (a simple proof).
"""
import os

from conan import ConanFile


class RocqTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        bin_dir = os.path.join(self.dependencies["rocq"].package_folder, "bin")
        rocq = os.path.join(bin_dir, "rocq")
        test_file = os.path.join(self.source_folder, "test_rocq.v")
        
        if os.path.isfile(rocq):
            self.run(f'"{rocq}" --version', env="conanrun")
            if os.path.isfile(test_file):
                self.run(f'"{rocq}" -q -compile "{test_file}"', env="conanrun")
        else:
            self.run("rocq --version", env="conanrun")
