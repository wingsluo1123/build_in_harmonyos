#!/usr/bin/env python3
"""Conan test_package — jwt-cli (Rust CLI binary tool).

L1 test: verify jwt binary exists and runs correctly.
"""
import os
from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.env import VirtualRunEnv


class JwtcliTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str, run=True)

    def generate(self):
        runenv = VirtualRunEnv(self)
        runenv.generate()

    def build(self):
        pass  # Nothing to build - just testing the binary

    def test(self):
        if not cross_building(self):
            # Use conanrun env which should have PATH with bindirs
            self.run("jwt --version", env="conanrun")
