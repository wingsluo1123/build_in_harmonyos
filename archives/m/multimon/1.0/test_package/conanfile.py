import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv


class MultimonTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        package_bin = os.path.join(self.dependencies["multimon"].package_folder, "bin")
        for command in ("multimon", "gen"):
            path = os.path.join(package_bin, command)
            if not os.path.isfile(path):
                raise RuntimeError(f"missing packaged command: {path}")
        if not can_run(self):
            self.output.warning("runtime execution is unavailable for this profile")
            return
        script = os.path.join(self.source_folder, "test_multimon.py")
        self.run(
            shlex.join(["python3", script, package_bin]),
            env="conanrun",
        )
