#!/usr/bin/env python3
"""Conan test_package for minisign CLI tool.

R34: The test substantively depends on the minisign binary.
It runs `minisign -v` to verify the binary is functional.
"""
import os

from conan import ConanFile


class MinisignTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
