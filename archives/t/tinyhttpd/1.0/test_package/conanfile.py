#!/usr/bin/env python3
"""Conan test_package for tinyhttpd 1.0.

R34: Test must actually depend on the tested package.
tinyhttpd is a CLI HTTP server — the test starts the binary,
verifies it runs, and cleans up.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class TinyhttpdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Actually execute the tested binary
        dep = self.dependencies["tinyhttpd"]
        httpd_bin = os.path.join(dep.package_folder, "bin", "httpd")
        test_script = os.path.join(self.source_folder, "test_tinyhttpd.sh")
        if can_run(self):
            self.run(
                f'sh "{test_script}" "{httpd_bin}"',
                env="conanrun",
            )
