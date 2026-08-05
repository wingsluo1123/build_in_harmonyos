#!/usr/bin/env python3
"""Conan test_package for codespell 2.4.2 — verifies codespell CLI works."""
import os
import sys

from conan import ConanFile


class CodespellTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        dep = self.dependencies["codespell"]
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_pkgs = os.path.join(dep.package_folder, "lib", py_ver, "site-packages")
        codespell_bin = os.path.join(dep.package_folder, "bin", "codespell")
        # R34: test must exercise the actual package — run codespell --version
        self.run(
            f'{bash} -c "PYTHONPATH={site_pkgs}:$PYTHONPATH '
            f'python3 {codespell_bin} --version"',
            env="conanrun",
        )
        # Also run the functional test source (test_codespell.py)
        test_script = os.path.join(os.path.dirname(__file__), "test_codespell.py")
        self.run(
            f'{bash} -c "PYTHONPATH={site_pkgs}:$PYTHONPATH '
            f'CODESPELL_BIN={codespell_bin} python3 {test_script}"',
            env="conanrun",
        )
