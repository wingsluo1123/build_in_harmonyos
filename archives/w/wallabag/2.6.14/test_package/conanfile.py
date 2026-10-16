#!/usr/bin/env python3
"""test_package for wallabag 2.6.14 — installed-package consumer check.

Runs test_wallabag.py (python3, always available) against the staged
share/wallabag tree. The driver performs structural consumer checks itself
and, when a system php interpreter exists, folds in the real php consumer
suite (test_wallabag.php) plus the shell harness (test_wallabag.sh) and
emits the single HMBS_TEST_PACKAGE_RESULT marker.

No tool_requires is declared: the conan ohpcd remote hosts no php recipe,
so a hard php requirement would fail dependency-graph resolution before any
test code runs. All paths into the tested package are absolute, so the L1e
destructive check (removing share/) fails as required.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException


class WallabagTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["wallabag"].package_folder
        share = os.path.join(pkg, "share", "wallabag")
        if not os.path.isdir(share):
            raise ConanException(f"wallabag share tree missing: {share}")
        for required in ("app/config/wallabag.yml", "vendor/autoload.php",
                         "bin/console"):
            if not os.path.isfile(os.path.join(share, required)):
                raise ConanException(f"wallabag bundle incomplete, missing: {required}")

        tdir = os.path.dirname(__file__)
        driver = os.path.join(tdir, "test_wallabag.py")
        if not os.path.isfile(driver):
            raise ConanException(f"test_wallabag.py missing: {driver}")

        python = shutil.which("python3") or shutil.which("python")
        if python is None:
            raise ConanException("python3 interpreter not found for test driver")
        self.run(f'"{python}" --version')
        self.run(f'"{python}" "{driver}" "{share}"', env="conanrun")
