#!/usr/bin/env python3
"""Test package for swirc.

Test strategy (executed by test.sh, see CI gate L0c):
- L1 smoke: swirc --version runs and returns 0
- OHOS consumer (rule12): Construct input → real execution → verify output → check result
"""
import os

from conan import ConanFile


class SwircTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        """Run test.sh: L1 smoke + OHOS rule12 consumer e2e.

        Both cases are non-assertion: judged by process exit code
        (self.run raises ConanException on non-zero exit).
        """
        # OHOS: /system/bin/sh (mksh) may not execute ELF binaries reliably.
        # Use bash to wrap binary execution (aa3d precedent).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
