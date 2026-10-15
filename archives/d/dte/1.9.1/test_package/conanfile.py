#!/usr/bin/env python3
"""test_package for dte 1.9.1 — runs test.sh (CLI smoke + termios raw-mode pty probe)."""

import os

from conan import ConanFile


class DteTestConan(ConanFile):
    """test_package for dte — CLI smoke tests plus a termios raw-mode pty probe."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
