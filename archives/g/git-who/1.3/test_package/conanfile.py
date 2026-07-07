#!/usr/bin/env python3
"""test_package for git-who — CLI smoke test."""
import os
from conan import ConanFile

class GitWhoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["git-who"]
        bin_dir = dep.cpp_info.bindirs[0] if dep.cpp_info.bindirs else os.path.join(dep.package_folder, "bin")
        bin_path = os.path.join(bin_dir, "git-who")
        assert os.path.isfile(bin_path), f"git-who not found at {bin_path}"

        # Test --version
        rc = self.run(f"{bin_path} -version", ignore_errors=True)
        assert rc == 0, "git-who -version failed"

        # Test --help
        rc = self.run(f"{bin_path} --help", ignore_errors=True)
        assert rc == 0, "git-who --help failed"
