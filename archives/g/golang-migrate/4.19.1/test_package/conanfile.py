#!/usr/bin/env python3
"""Conan test_package for golang-migrate 4.19.1 — consumer smoke test.

golang-migrate is a Go CLI application (not a linkable C/C++ library).
The consumer test runs the packaged `migrate` binary with `-help` and
asserts:
  - exit code 0
  - stdout mentions stable driver keywords (postgres, mysql, sqlite, file)

File location: archives/g/golang-migrate/4.19.1/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class GolangMigrateTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["golang-migrate"].package_folder
        exe_name = "migrate.exe" if str(self.settings.os) == "Windows" else "migrate"
        bin_path = os.path.join(package_folder, "bin", exe_name)
        assert os.path.isfile(bin_path), f"migrate binary not found: {bin_path}"

        if can_run(self):
            test_script = os.path.join(self.recipe_folder, "test.sh")
            self.run(f'bash "{test_script}" "{bin_path}"', env="conanrun")
        else:
            # Cross-compile host: validate ELF magic only (cannot execute target binary).
            with open(bin_path, "rb") as binary:
                magic = binary.read(4)
            assert magic == b"\x7fELF", f"migrate is not an ELF binary: {magic!r}"
            self.output.info(f"migrate binary exists and has ELF magic: {bin_path}")
