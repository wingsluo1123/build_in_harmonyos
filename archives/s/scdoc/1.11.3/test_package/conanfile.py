#!/usr/bin/env python3
"""Conan test_package for scdoc 1.11.3 — smoke test.

Verifies that the scdoc binary is functional after installation.
Creates a simple .scd input file, runs scdoc on it, and checks the output
contains expected roff-formatted content.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class ScdocTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
            # Use bash to wrap binary execution.
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            self.run(f'{bash} test.sh', env="conanrun")
