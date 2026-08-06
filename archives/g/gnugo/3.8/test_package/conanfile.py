import os

from conan import ConanFile


class GnugoTestConan(ConanFile):
    """test_package for gnugo — runs gnugo --version to verify the binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Execute the gnugo binary to verify it works
        self.run("gnugo --version", env="conanrun")
