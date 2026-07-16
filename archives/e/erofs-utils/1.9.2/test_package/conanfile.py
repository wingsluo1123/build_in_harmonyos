import os

from conan import ConanFile
from conan.tools.build import can_run


class ErofsUtilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            script = os.path.join(self.source_folder, "test_erofs_utils.sh")
            self.run(f'bash "{script}"', env="conanrun")
