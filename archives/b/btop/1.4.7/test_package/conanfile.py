#!/usr/bin/env python3
"""Conan test_package for btop 1.4.7 — verifies the btop binary works."""

import os

from conan import ConanFile


class BtopTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh cannot execute ELF binaries, use bash wrapper
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        btop = os.path.join(self.dependencies["btop"].package_folder, "bin", "btop")
        test_script = os.path.join(self.source_folder, "test_btop.sh")
        self.run(f'"{bash}" "{test_script}" "{btop}"', env="conanrun")
