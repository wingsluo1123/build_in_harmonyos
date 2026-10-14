#!/usr/bin/env python3
"""Consumer test for the packaged uMurmur daemon."""

import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment


class UmurmurTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str, run=True)
        self.requires("openssl/3.5.8.1", run=True)

    def test(self):
        package_folder = self.dependencies["umurmur"].package_folder
        script = os.path.join(self.recipe_folder, "test_umurmur.py")
        python = shutil.which("python3") or shutil.which("python")
        if not python:
            raise RuntimeError("python3 is required for the uMurmur consumer test")

        test_env = Environment()
        runner = self.conf.get("user.libminini:qemu_runner", default="", check_type=str)
        if runner:
            test_env.define("UMURMUR_TEST_RUNNER", runner)

        with test_env.vars(self).apply():
            self.run(f'"{python}" "{script}" "{package_folder}"', env="conanrun")
