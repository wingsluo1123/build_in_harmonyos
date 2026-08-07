#!/usr/bin/env python3
"""Test package for postgresql-hypopg 1.4.2 conan recipe.

HypoPG is a PostgreSQL extension (.so file). The test verifies that
the package contains the expected extension files by running a shell
script that checks file existence, ELF validity, and extension metadata.
"""
import os

from conan import ConanFile


class PostgresqlHypopgTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get the package root path
        dep = self.dependencies["postgresql-hypopg"]
        rootpath = str(dep.package_folder)

        # Run the test script with self.run() (required by CI L0d gate)
        test_script = os.path.join(self.source_folder, "test_hypopg.sh")
        self.run(f'sh "{test_script}" "{rootpath}"', env="conanrun")
