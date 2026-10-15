#!/usr/bin/env python3
"""Conan test_package for lambda-align 1.0.3 (CLI tools).

Executes the packaged binaries `lambda` and `lambda_indexer` via the
test_lambda.sh driver script (R34: real binary invocation).
"""
from conan import ConanFile


class LambdaalignTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # conanrun env injects the dependency's bin/ into PATH; the .sh
        # driver actually runs both binaries and asserts their output.
        self.run("sh test_lambda.sh", env="conanrun")
