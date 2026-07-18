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
            package_folder = self.dependencies["erofs-utils"].package_folder
            self.run(
                f'bash "{script}" "{package_folder}"',
                env="conanrun",
            )
