"""Conan test_package for samurai — verifies the samu binary works."""
import os

from conan import ConanFile


class SamuraiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        self.run("samu --version", env="conanrun")
