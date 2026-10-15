#!/usr/bin/env python3
"""Consumer test for the packaged MVDSV server."""

import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment


class MvdsvTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str, run=True)

    def test(self):
        package_folder = self.dependencies["mvdsv"].package_folder
        script = os.path.join(self.recipe_folder, "test_mvdsv.py")
        python = shutil.which("python3") or shutil.which("python")
        if not python:
            raise RuntimeError("python3 is required for the MVDSV consumer test")
        runner = self.conf.get("user.libminini:qemu_runner", default="")
        environment = Environment()
        environment.define("MVDSV_TEST_RUNNER", str(runner))
        with environment.vars(self).apply():
            self.run(f'"{python}" "{script}" "{package_folder}"', env="conanrun")
