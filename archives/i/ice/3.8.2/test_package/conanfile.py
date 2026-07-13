#!/usr/bin/env python3
"""Conan test_package — Ice 3.8.2 smoke test.

Verifies package-provided binaries from the tested package:
- icebox --version reports the packaged Ice version
- slice2cpp can compile a static Slice test source
"""
import os

from conan import ConanFile


class IceTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        script = os.path.join(self.source_folder, "test.sh")
        slice_file = os.path.join(self.source_folder, "Test.ice")
        self.run(f"sh {script} {slice_file}", env="conanrun")
