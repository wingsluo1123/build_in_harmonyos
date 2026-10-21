#!/usr/bin/env python3
"""Conan consumer test for the installed pglast 8.2 package."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class PglastTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str, headers=False, libs=False, run=True)

    def test(self):
        if can_run(self):
            script = os.path.join(self.source_folder, "test_pglast.py")
            self.run(f'python3 "{script}"', env="conanrun")
            if self.settings.os == "OHOS":
                platform_script = os.path.join(self.source_folder, "test_harmonyos.py")
                self.run(f'python3 "{platform_script}"', env="conanrun")
