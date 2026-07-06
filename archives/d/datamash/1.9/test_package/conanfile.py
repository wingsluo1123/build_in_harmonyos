#!/usr/bin/env python3
"""Conan test_package — datamash 1.9

datamash is a CLI tool, not a library. Test by running the binary.
"""
import os

from conan import ConanFile


class DatamashTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # Find the datamash binary in the package folder
        dep = self.dependencies["datamash"]
        pf = dep.package_folder
        if pf:
            bin_path = os.path.join(pf, "bin", "datamash")
            if os.path.exists(bin_path):
                self.run(f'"{bin_path}" --version')
                return
        # Fallback: try from PATH
        self.run("datamash --version", env="conanrun")
