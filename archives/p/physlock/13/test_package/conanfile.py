import os
import shlex
import sys

from conan import ConanFile
from conan.tools.build import can_run


class PhyslockTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.recipe_folder, "test_physlock.py")
        runtime = "1" if can_run(self) else "0"
        self.run(
            f"{shlex.quote(sys.executable)} {shlex.quote(script)} "
            f"{shlex.quote(package)} {runtime}",
            env="conanrun",
        )
