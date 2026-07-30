from conan import ConanFile
from conan.tools.build import can_run
import os

class DocuumTestPkgConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_library_str)

    def build(self):
        pass

    def test(self):
        if can_run(self):
            self.run("docuum --help", env="conanrun")
