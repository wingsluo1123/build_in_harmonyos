#!/usr/bin/env python3
"""Conan test package for the installed ladvd command-line programs."""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class LadvdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies["ladvd"].package_folder
        bin_dir = os.path.join(package, "bin")
        commands = [os.path.join(bin_dir, name) for name in ("ladvd", "ladvdc")]
        missing = [path for path in commands if not os.path.isfile(path)]
        if missing:
            raise ConanException("missing packaged command(s): " + ", ".join(missing))

        native_ohos = self.settings.os != "OHOS" or os.uname().sysname in (
            "HarmonyOS",
            "OHOS",
        )
        if not can_run(self) or not native_ohos:
            self.output.warning("Cross build: packaged commands verified but not executed")
            return

        script = os.path.join(self.source_folder, "test_ladvd.py")
        self.run(
            shlex.join(["python3", script, bin_dir]),
            env="conanrun",
        )
