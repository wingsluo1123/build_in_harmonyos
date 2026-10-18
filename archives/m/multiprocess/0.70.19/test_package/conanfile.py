"""Exercise installed artifacts and their declared runtime dependency."""
import os
import sys
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment


class MultiprocessTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str, headers=False, libs=False, run=True)

    def test(self):
        if can_run(self):
            environment = Environment()
            environment.define("PYTHONDONTWRITEBYTECODE", "1")
            environment.define("PYTHONNOUSERSITE", "1")
            with environment.vars(self).apply():
                script = os.path.join(self.source_folder, "test_multiprocess.py")
                self.run(f'"{sys.executable}" -s "{script}"', env="conanrun")
