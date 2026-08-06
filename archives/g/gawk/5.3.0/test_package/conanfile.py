#!/usr/bin/env python3
"""Conan test_package for gawk 5.3.0.

Smoke test for the gawk CLI tool.
Upstream has an extensive test suite (make check); this test_package
exercises the binary from a consumer perspective:
  1. gawk --version (binary runs, shows version)
  2. gawk arithmetic (exit code verifies correctness)
  3. gawk field processing (exit code verifies field extraction)
"""
import os

from conan import ConanFile


class GawkTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # 1. Version check
        self.run("gawk --version", env="conanrun")

        # 2. Arithmetic: 1+2*3 should equal 7
        self.run("gawk 'BEGIN {exit (1+2*3==7) ? 0 : 1}'", env="conanrun")

        # 3. Field extraction: create input file, verify $1=="hello"
        test_input = os.path.join(self.build_folder, "gawk_test_input.txt")
        with open(test_input, "w") as f:
            f.write("hello world\n")
        self.run(
            "gawk '{exit ($1==\"hello\") ? 0 : 1}' " + test_input,
            env="conanrun",
        )
