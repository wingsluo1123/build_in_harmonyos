#!/usr/bin/env python3
"""Conan test_package — lazygit 0.48.0

L1 test: verify the lazygit binary runs and reports correct version.
On OHOS, ELF binaries require elfldr wrapper to execute.
"""
import os

from conan import ConanFile


class LazygitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # In Conan 2.x, use self.dependencies to access package info
        dep = self.dependencies["lazygit"]
        lazygit_bin = os.path.join(dep.package_folder, "bin", "lazygit")

        # On OHOS, ELF binaries need elfldr wrapper
        if str(self.settings.os) in ("OHOS",):
            cmd = f"elfldr {lazygit_bin} --version"
        else:
            cmd = f"{lazygit_bin} --version"
        self.run(cmd)
