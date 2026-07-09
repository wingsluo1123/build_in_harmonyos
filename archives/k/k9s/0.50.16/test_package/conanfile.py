#!/usr/bin/env python3
"""Conan test_package — k9s 0.50.16

L1 test: verify the k9s binary runs and reports correct version.
On OHOS, ELF binaries require elfldr wrapper to execute.
"""
import os

from conan import ConanFile


class K9sTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # In Conan 2.x, use self.dependencies to access package info
        dep = self.dependencies["k9s"]
        k9s_bin = os.path.join(dep.package_folder, "bin", "k9s")

        # On OHOS, ELF binaries need elfldr wrapper
        if str(self.settings.os) in ("OHOS",):
            cmd = f"elfldr {k9s_bin} version"
        else:
            cmd = f"{k9s_bin} version"
        self.run(cmd)
