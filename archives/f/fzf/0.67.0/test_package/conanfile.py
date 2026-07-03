#!/usr/bin/env python3
"""Conan test_package — fzf 0.67.0

L1 test: verify the fzf binary runs and reports correct version.
On OHOS, ELF binaries require elfldr wrapper to execute.
"""
import os

from conan import ConanFile


class FzfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # In Conan 2.x, use self.dependencies to access package info
        dep = self.dependencies["fzf"]
        fzf_bin = os.path.join(dep.package_folder, "bin", "fzf")

        # On OHOS, ELF binaries need elfldr wrapper
        if str(self.settings.os) in ("OHOS",):
            cmd = f"elfldr {fzf_bin} --version"
        else:
            cmd = f"{fzf_bin} --version"
        self.run(cmd)
