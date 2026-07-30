import os

from conan import ConanFile


class BlenderTestConan(ConanFile):
    """test_package for blender - verifies the headless build works"""
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Blender is an application, test via executable
        self.run("blender --version", env="conanrun")
