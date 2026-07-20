from conan import ConanFile
from conan.tools.build import cross_building
import os

class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not cross_building(self):
            self.run("pkg-config --exists atk", env="conanrun")
