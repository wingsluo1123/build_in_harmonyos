#!/usr/bin/env python3
"""Test package — postgresql-topn 2.7.0"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class PostgresqlTopnTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        # Get the package folder from dependencies
        pkg = self.dependencies["postgresql-topn"]
        package_dir = pkg.package_folder

        # Run the artifact verification test
        test_script = os.path.join(self.source_folder, "test.sh")
        self.run(f"bash {test_script} {package_dir}", env="conanrun")
