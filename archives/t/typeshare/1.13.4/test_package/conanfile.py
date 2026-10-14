#!/usr/bin/env python3
"""Conan consumer test for typeshare 1.13.4 (Rust binary package).

Two layers of verification:

  1. package integrity — the packaged `typeshare` executable exists;
  2. consumer smoke + functional + HarmonyOS traits — test_typeshare.py runs
     the binary, asserts AArch64 / OHOS musl loader / OHOS code signature, then
     exercises the real functionality: a `#[typeshare]` annotated Rust source is
     translated to real TypeScript / Swift / Kotlin / Scala output files.
"""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class TypeshareTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"
    exports_sources = "test_typeshare.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        package_folder = self.dependencies["typeshare"].package_folder
        exe = os.path.join(package_folder, "bin", "typeshare")
        if not os.path.isfile(exe):
            raise AssertionError(f"Missing typeshare executable: {exe}")

        if not can_run(self):
            self.output.info("Cross-building: verified package layout only.")
            return

        script = os.path.join(self.source_folder, "test_typeshare.py")
        result = self.run(
            f'PACKAGE_FOLDER="{package_folder}" "{sys.executable}" "{script}"',
            env="conanrun",
            ignore_errors=True,
        )
        if result != 0:
            raise AssertionError(
                f"typeshare test_package failed with exit code {result}"
            )
