import os

from conan import ConanFile


class RoverTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_dir = self.dependencies["rover"].package_folder
        bin_path = os.path.join(bin_dir, "bin", "rover")
        test_script = os.path.join(self.source_folder, "test.sh")
        self.run(f'chmod +x "{test_script}" && "{test_script}" "{bin_path}"', env="conanrun")
