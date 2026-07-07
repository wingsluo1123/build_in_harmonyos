#!/usr/bin/env python3
"""test_package for bazel-diff — CLI smoke test."""
import os
from conan import ConanFile

class BazelDiffTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["bazel-diff"]
        bin_dir = dep.cpp_info.bindirs[0] if dep.cpp_info.bindirs else os.path.join(dep.package_folder, "bin")
        launcher = os.path.join(bin_dir, "bazel-diff")
        assert os.path.isfile(launcher), f"bazel-diff launcher not found at {launcher}"
        rc = self.run(f"{launcher} --help", ignore_errors=True)
        assert rc == 0, "bazel-diff --help failed"
