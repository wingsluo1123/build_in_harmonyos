#!/usr/bin/env python3
"""Conan test_package for txacme 0.9.3 — pure-Python (python-require) package.

Runs the consumer + HarmonyOS-specific verification (test_txacme.py) against the
packaged library. The full upstream ``trial`` suite is executed separately (see
test_package/MANIFEST.yml and the PR test report); it is also re-run here on a
best-effort basis when the Twisted runtime is importable.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class TxacmeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "test_txacme.py"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            raise ConanException("the target Python runtime is unavailable")
        pkg = self.dependencies["txacme"].package_folder
        site = os.path.join(pkg, "lib", "python3.12", "site-packages")
        script = os.path.join(self.source_folder, "test_txacme.py")
        self.run(f'python3 "{script}" "{site}" "{pkg}"', env="conanrun")
