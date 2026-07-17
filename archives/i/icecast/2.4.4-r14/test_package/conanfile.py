import os

from conan import ConanFile
from conan.tools.build import can_run


class IcecastTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            binary = os.path.join(
                self.dependencies["icecast"].package_folder,
                "bin",
                "icecast",
            )
            script = os.path.join(self.source_folder, "test.sh")
            self.run(f'sh "{script}" "{binary}"', env="conanrun")
