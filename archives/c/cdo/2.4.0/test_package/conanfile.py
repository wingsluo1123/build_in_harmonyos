#!/usr/bin/env python3
"""Conan test_package — cdo 2.4.0.

R34: Test actually executes cdo binary to verify it works.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class CdoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
            script = os.path.join(self.source_folder, "test.sh")
            self.run(f'"{bash}" "{script}"', env="conanrun")
            self.output.success("Conan test_package: success")
