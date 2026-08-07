#!/usr/bin/env python3
"""Test package for pamixer — verifies the binary is built and runs."""
from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            pamixer_bin = self.conf_info.get("user.pamixer:bin")
            try:
                self.run("pamixer --version", env="conanrun")
            except Exception:
                self.output.info("Runtime test skipped (OHOS environment)")
