#!/usr/bin/env python3
"""Conan test_package for attrs 26.1.0 — Python library.

Verifies the attr package is installed and its core API works:
defines a class with attr.s/attr.ib and instantiates it.
"""
import os

from conan import ConanFile


class AttrsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        site = os.path.join(self.dependencies["attrs"].package_folder,
                            "lib", "python3.12", "site-packages")
        os.environ["PYTHONPATH"] = site
        # Use attr.make_class to verify the core API works (single-line, no decorator syntax)
        self.run(
            'python3 -c "import attr; '
            'C = attr.make_class(\'Point\', [\'x\', \'y\']); '
            'p = C(1, 2); '
            'assert p.x == 1 and p.y == 2; '
            'print(attr.__name__, C.__name__)"'
        )