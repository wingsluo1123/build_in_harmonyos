from conan import ConanFile
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.files import get
import os


class HexeditTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        AutotoolsDeps(self).generate()
        AutotoolsToolchain(self).generate()

    def build(self):
        self.run("hexedit --help", env="conanrun")

    def test(self):
        self.run("hexedit --help", env="conanrun")
