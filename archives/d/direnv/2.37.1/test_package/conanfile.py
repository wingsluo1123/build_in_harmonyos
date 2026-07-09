#!/usr/bin/env python3
"""Conan test_package — direnv 2.37.1

L1 test: verify the direnv binary runs and reports correct version.
On OHOS, ELF binaries require elfldr wrapper to execute.
"""
import os

from conan import ConanFile


class DirenvTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # In Conan 2.x, use self.dependencies to access package info
        dep = self.dependencies["direnv"]
        direnv_bin = os.path.join(dep.package_folder, "bin", "direnv")

        # On OHOS, ELF binaries need elfldr wrapper
        if str(self.settings.os) in ("OHOS",):
            cmd = f"elfldr {direnv_bin} --version"
        else:
            cmd = f"{direnv_bin} --version"
        self.run(cmd)
