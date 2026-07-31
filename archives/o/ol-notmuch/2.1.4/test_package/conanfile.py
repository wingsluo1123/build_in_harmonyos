#!/usr/bin/env python3
"""Conan test_package for ol-notmuch 2.1.4."""
import os
import sys

from conan import ConanFile


class OlNotmuchTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["ol-notmuch"].package_folder
        root = os.path.join(pkg, "share", "ol-notmuch")
        script = os.path.join(self.recipe_folder, "test_ol_notmuch.py")
        self.run(f'"{sys.executable}" "{script}" "{root}"', env="conanrun")
