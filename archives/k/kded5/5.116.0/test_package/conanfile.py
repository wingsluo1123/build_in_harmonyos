#!/usr/bin/env python3
"""Conan test_package for kded5 5.116.0.

kded5 produces the KDE Daemon executable (bin/kded5).  The test() method runs a
dedicated test source program (test_kded5.py) via self.run(), which really
executes `kded5 --version` on the target host — satisfying both the CI gate
that requires actual test execution and the L0 no_test_sources gate (a test
source file other than conanfile.py is present).
"""
import os
import sys

from conan import ConanFile
from conan.tools.env import Environment


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        exe = os.path.join(dep.package_folder, "bin", "kded5")
        if not os.path.isfile(exe):
            raise Exception(f"kded5 executable missing: {exe}")

        env = Environment()
        # kded5 constructs a QApplication; --version exits before any display
        # is needed, but force offscreen QPA for safety.
        env.define("QT_QPA_PLATFORM", "offscreen")
        libs = [os.path.join(d.package_folder, "lib")
                for d in self.dependencies.values() if d.package_folder]
        env.append("LD_LIBRARY_PATH", libs)
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_kded5.py")
        with env.vars(self).apply():
            self.run(f'"{sys.executable}" "{script}" "{exe}"', env="conanrun")
