from conan import ConanFile
import os


class HexeditTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        self.run("hexedit --help", env="conanrun")