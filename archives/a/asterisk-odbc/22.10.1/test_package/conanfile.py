#!/usr/bin/env python3
"""Conan test_package - asterisk-odbc 22.10.1."""

import os
import pathlib
import sys

from conan import ConanFile


class AsteriskOdbcTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["asterisk-odbc"].package_folder
        probe = pathlib.Path(self.source_folder) / "test_asterisk_odbc.py"
        self.run(f'"{sys.executable}" "{probe}" "{pkg}"', env="conanrun")

        module_dir = os.path.join(pkg, "lib", "asterisk", "modules")
        for module in (
            "res_odbc_transaction.so",
            "res_odbc.so",
            "res_config_odbc.so",
            "func_odbc.so",
            "cdr_odbc.so",
            "cdr_adaptive_odbc.so",
            "cel_odbc.so",
        ):
            path = os.path.join(module_dir, module)
            self.run(f'ls -lh "{path}"', env="conanrun")

