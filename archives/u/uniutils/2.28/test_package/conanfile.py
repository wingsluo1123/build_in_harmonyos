#!/usr/bin/env python3
"""Consumer test for the installed uniutils command set."""

import os

from conan import ConanFile


class UniutilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["uniutils"]
        bindir = os.path.join(dep.package_folder, "bin")
        self.run(f'UNIUTILS_BIN="{bindir}" sh test.sh', env="conanrun")
