#!/usr/bin/env python3
"""Conan test_package — codebook-lsp 0.3.41 (Rust binary).

codebook-lsp is a Rust/Cargo binary, not a C/C++ library.
This test package verifies the binary is executable and reports
the correct version string via `codebook-lsp --version`.

File location: archives/{letter}/codebook-lsp/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile


class CodebookLspTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Run the installed binary to verify it is functional.
        # codebook-lsp --version prints the version string and exits 0.
        # The test.sh script wraps this with an explicit version check.
        test_script = os.path.join(self.recipe_folder, "test.sh")
        self.run(f"sh {test_script}", env="conanrun")
