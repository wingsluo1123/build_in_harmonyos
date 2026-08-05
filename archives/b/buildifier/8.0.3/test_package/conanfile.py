#!/usr/bin/env python3
"""Conan test_package for buildifier 8.0.3 — consumer smoke test.

buildifier is a Go CLI tool (not a linkable C/C++ library). The consumer
test runs the packaged `buildifier` binary with --version and --mode=check
to verify it is functional.

File location: archives/b/buildifier/8.0.3/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class BuildifierTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["buildifier"].package_folder
        bin_path = os.path.join(package_folder, "bin", "buildifier")
        assert os.path.isfile(bin_path), f"buildifier binary not found: {bin_path}"

        if can_run(self):
            test_script = os.path.join(self.recipe_folder, "test.sh")
            self.run(f'bash "{test_script}" "{bin_path}"', env="conanrun")
        else:
            # Cross-compile host: validate ELF magic only (cannot execute target binary).
            with open(bin_path, "rb") as binary:
                magic = binary.read(4)
            assert magic == b"\x7fELF", f"buildifier is not an ELF binary: {magic!r}"
            self.output.info(f"buildifier binary exists and has ELF magic: {bin_path}")
