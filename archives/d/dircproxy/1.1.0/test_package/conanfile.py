#!/usr/bin/env python3
"""Conan test_package — dircproxy 1.1.0
dircproxy is a CLI tool, not a library. Test by running the binary.
"""
import os

from conan import ConanFile


class DircproxyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        dep = self.dependencies["dircproxy"]
        pf = dep.package_folder
        if pf:
            bin_path = os.path.join(pf, "bin", "dircproxy")
            if os.path.exists(bin_path):
                self.run(f'"{bin_path}" --version')
                return
        self.run("dircproxy --version", env="conanrun")
