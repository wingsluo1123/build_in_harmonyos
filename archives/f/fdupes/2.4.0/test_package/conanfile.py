import os

from conan import ConanFile


class FdupesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # The conanrun env should have the bin path from bindirs
        # Use a command that sources conanrun.sh first
        self.run("fdupes --version", env="conanrun")
