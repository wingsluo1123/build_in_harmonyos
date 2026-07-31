import os
import sys

from conan import ConanFile


class SafekeepTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        package_folder = dep.package_folder
        script = os.path.join(self.recipe_folder, "test_safekeep_package.py")
        self.run(f'"{sys.executable}" "{script}" "{package_folder}"', env="conanrun")
