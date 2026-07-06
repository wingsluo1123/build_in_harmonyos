#!/usr/bin/env python3
"""test_package for vacuum — CLI smoke test.

Tests that the vacuum binary is installed and responds to basic commands.
"""
import os

from conan import ConanFile


class VacuumTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R32: support both Linux and OHOS
        # Conan 2.x: use self.dependencies to access dependency info
        dep = self.dependencies["vacuum"]
        bin_dir = dep.cpp_info.bindirs[0] if dep.cpp_info.bindirs else os.path.join(dep.package_folder, "bin")
        bin_path = os.path.join(bin_dir, "vacuum")
        assert os.path.isfile(bin_path), f"vacuum binary not found at {bin_path}"

        # Test 2: version works
        rc = self.run(f"{bin_path} version", ignore_errors=True)
        assert rc == 0, "vacuum version failed"

        # Test 3: help works
        rc = self.run(f"{bin_path} --help", ignore_errors=True)
        assert rc == 0, "vacuum --help failed"
