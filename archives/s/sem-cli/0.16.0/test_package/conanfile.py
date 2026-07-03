import os
from conan import ConanFile
from conan.tools.build import can_run


class SemCliTestPackage(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.dependencies["sem-cli"].package_folder, "bin", "sem")
            self.run(f'"{bin_path}" --version', env="conanrun")
