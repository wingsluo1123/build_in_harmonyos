#!/usr/bin/env python3
"""Conan test_package for aws-shell — verifies CLI entry points.

aws-shell is a Python application with pip-based runtime dependencies
(botocore, awscli, prompt-toolkit, etc.) that are not available as conan
packages. The test verifies package structure and entry point presence
using test.sh which runs with the conanrun environment.
"""
import os

from conan import ConanFile


class AwsShellTestConan(ConanFile):
    """test_package for aws-shell — runs test.sh which verifies the package."""
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
