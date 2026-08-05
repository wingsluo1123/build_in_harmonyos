#!/usr/bin/env python3
"""Conan test_package for argo 4.0.5 — consumer smoke test.

argo is a Go CLI application (not a linkable C/C++ library). The consumer test
runs the packaged `argo` binary with `version` and `help` subcommands and asserts:
  - `argo version` exits 0 and prints version info
  - `argo help` exits 0 and lists subcommands

File location: archives/a/argo/4.0.5/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class ArgoTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["argo"].package_folder
        exe_name = "argo.exe" if str(self.settings.os) == "Windows" else "argo"
        bin_path = os.path.join(package_folder, "bin", exe_name)
        assert os.path.isfile(bin_path), f"argo binary not found: {bin_path}"

        if can_run(self):
            test_script = os.path.join(self.recipe_folder, "test.sh")
            self.run(f'bash "{test_script}" "{bin_path}"', env="conanrun")
        else:
            # Cross-compile host: validate ELF magic only (cannot execute target binary).
            with open(bin_path, "rb") as binary:
                magic = binary.read(4)
            assert magic == b"\x7fELF", f"argo is not an ELF binary: {magic!r}"
            self.output.info(f"argo binary exists and has ELF magic: {bin_path}")
