"""Exercise the installed Python extension and its real LevelDB dependency."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class PlyvelTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str, headers=False, libs=False, run=True)

    def test(self):
        if can_run(self):
            self.run(f'python3 "{os.path.join(self.source_folder, "test_plyvel.py")}"',
                     env="conanrun")
