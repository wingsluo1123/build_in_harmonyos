import os
import sys

from conan import ConanFile


class PerlIpcShareliteTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("perl/5.42.2")

    def test(self):
        perl = os.path.join(self.dependencies["perl"].package_folder, "bin", "perl")
        script = os.path.join(self.recipe_folder, "test_perl_ipc_sharelite.py")
        self.run(f'"{sys.executable}" "{script}" "{perl}"', env="conanrun")
