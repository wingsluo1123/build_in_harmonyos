import os

from conan import ConanFile


class AlsaUtilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # R34: Test must substantively depend on the tested package.
        # Run aplay --version to verify the installed binary works.
        self.run("aplay --version", env="conanrun")
