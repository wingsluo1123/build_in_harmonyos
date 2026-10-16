#!/usr/bin/env python3
"""Installed-command consumer tests for vacation."""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration


class VacationTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration(
                "This consumer test exercises the installed command on OHOS"
            )
        package = self.dependencies["vacation"].package_folder
        executable = os.path.join(package, "bin", "vacation")
        script = os.path.join(self.source_folder, "test_vacation.py")
        self.run(
            shlex.join(["python3", script, executable]),
            env="conanrun",
        )
