#!/usr/bin/env python3
"""Conan test_package — cdo 2.4.0.

R34: Test actually executes cdo binary to verify it works.
"""
import os

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
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            self.run(f"{bash} test.sh", env="conanrun")
            self.output.success("Conan test_package: success")
