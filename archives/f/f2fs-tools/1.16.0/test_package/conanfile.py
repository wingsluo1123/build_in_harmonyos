import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class F2fsToolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        script = os.path.join(self.source_folder, "run_consumer_checks.py")
        command = f'"{sys.executable}" "{script}"'
        if not can_run(self):
            target = f"{self.settings.os}/{self.settings.arch}"
            build = f"{self.settings_build.os}/{self.settings_build.arch}"
            command += f' --runtime-unavailable "{target}" "{build}"'
        self.run(
            command,
            cwd=self.source_folder,
            env="conanrun",
        )
