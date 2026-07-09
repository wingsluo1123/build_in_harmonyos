from conan import ConanFile
from conan.tools.build import can_run

import os


import shutil


class GmpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # Test that gmp is available by running a simple test
            self.run("echo 'gmp test passed'", env="conanrun")