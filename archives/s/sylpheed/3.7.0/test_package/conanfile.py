#!/usr/bin/env python3
"""test_package for sylpheed 3.7.0 — consumer use case test.

sylpheed is a GTK+2 email client application. This test_package verifies:
  1. sylpheed binary exists and runs (--version, exit 0)
  2. libsylph shared library is a valid ELF arm64 shared object (consumer closure, HarmonyOS)
  3. GTK+2 shared lib is a valid ELF arm64 shared object (full consumer stack)

The checks are implemented in test_sylpheed.sh (invoked via CONFIG_SHELL bash,
the aa3d merged precedent for CLI-tool packages; no exec bit required on
HMDFS). OHOS has no ldd/readelf; `file` is used instead to confirm
loadability. --help is NOT tested: GTK+ apps return exit code 1 without a
display, which is normal behavior but would falsely fail self.run().
"""

import os

from conan import ConanFile


class SylpheedTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        sylpheed_bin = os.path.join(
            self.dependencies["sylpheed"].package_folder, "bin", "sylpheed")
        libsylph = os.path.join(
            self.dependencies["sylpheed"].package_folder, "lib",
            "libsylph-0.so.1.3.0")
        gtk2 = os.path.join(
            self.dependencies["gtk2"].package_folder, "lib",
            "libgtk-x11-2.0.so.0")

        test_script = os.path.join(os.path.dirname(__file__), "test_sylpheed.sh")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(
            f'"{bash}" "{test_script}" "{sylpheed_bin}" "{libsylph}" "{gtk2}"',
            env="conanrun")
