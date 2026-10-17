#!/usr/bin/env python3
"""Consumer test for the installed lxi-tools package."""

import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment


class LxiToolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str, run=True)

    def test(self):
        package_folder = self.dependencies["lxi-tools"].package_folder
        script = os.path.join(self.recipe_folder, "test_lxi_tools.py")
        python = shutil.which("python3") or shutil.which("python")
        if not python:
            raise RuntimeError("python3 is required for the lxi-tools consumer test")
        if not can_run(self):
            self.output.info("cross build: target execution is deferred to native OHOS validation")
            return
        environment = Environment()
        environment.define("LXI_EXPECT_OHOS", "1" if self.settings.os == "OHOS" else "0")
        with environment.vars(self).apply():
            self.run(f'"{python}" "{script}" "{package_folder}"', env="conanrun")
