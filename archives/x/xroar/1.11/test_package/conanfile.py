#!/usr/bin/env python3
"""Conan test_package for xroar 1.11.

XRoar ships no automated test suite, so this test exercises the *installed*
package from a consumer's perspective: run the packaged `xroar` binary and
verify its CLI contract (version banner, --help usage, deterministic failure
without ROMs).  All assertions run against the packaged bin/, not the source
tree.
"""
import os
import subprocess
import sys

from conan import ConanFile
from conan.tools.build import can_run


class XroarTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    generators = "VirtualRunEnv"

    def test(self):
        if not can_run(self):
            return
        dep = self.dependencies[self.tested_reference_str]
        bindir = os.path.join(dep.package_folder, "bin")
        script = os.path.join(self.recipe_folder, "test_xroar.py")
        # R34: actually execute the tested package's binary.
        self.run(f'"{sys.executable}" "{script}" "{bindir}"', env="conanrun")
