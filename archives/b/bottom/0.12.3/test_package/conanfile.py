#!/usr/bin/env python3
"""Conan test_package — bottom 0.12.3

L1 official test: verifies the btm binary is functional by running
`btm --version` and checking the output matches the expected version.
"""
import os

from conan import ConanFile


class BottomTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
