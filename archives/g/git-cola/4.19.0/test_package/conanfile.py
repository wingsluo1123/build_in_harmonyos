#!/usr/bin/env python3
"""Conan test_package for git-cola — Python application test.

Verifies that the cola Python module is importable and reports the correct version.
"""
import os

from conan import ConanFile


class GitColaTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get the package folder from the dependency
        dep = self.dependencies["git-cola"]
        pkg_folder = dep.package_folder
        site_packages = os.path.join(pkg_folder, "lib", "python3.12", "site-packages")

        # Test: import cola._version and verify version
        test_cmd = (
            'PYTHONPATH="' + site_packages + '" python3 -c '
            '"from cola._version import VERSION; '
            'assert VERSION == \'4.19.0\', VERSION; '
            'print(\'git-cola version:\', VERSION)"'
        )
        self.run(test_cmd, env="conanrun")
