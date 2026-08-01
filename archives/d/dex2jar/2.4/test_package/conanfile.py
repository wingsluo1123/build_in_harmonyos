#!/usr/bin/env python3
"""Conan test_package for dex2jar 2.4 — binary smoke test (R34).

Verifies the d2j-dex2jar script exists and runs via test.sh.
"""

import os

from conan import ConanFile


class Dex2JarTestPkgConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh cannot execute ELF binaries, use bash wrapper
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        dex2jar_home = self.dependencies["dex2jar"].package_folder
        test_script = os.path.join(self.source_folder, "test.sh")
        self.run(f'"{bash}" "{test_script}" "{dex2jar_home}"', env="conanrun")
