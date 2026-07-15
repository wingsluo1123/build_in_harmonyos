#!/usr/bin/env python3
"""Conan test_package — colordiff 1.0.22

Tests the colordiff binary by running test.sh which invokes the binary.
colordiff is a Perl script tool, not a library.
"""
import os

from conan import ConanFile


class ColordiffTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
