#!/usr/bin/env python3
"""Conan test_package — xorgrgb 1.1.1

Verifies that the showrgb binary is installed and functional.
Runs test.sh which invokes the binary (R34: substantive test).
"""
import os

from conan import ConanFile


class XorgrgbTestConan(ConanFile):
    """test_package for executable packages — runs test.sh which invokes the binary."""
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
