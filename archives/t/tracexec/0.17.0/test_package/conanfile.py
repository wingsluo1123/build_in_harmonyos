#!/usr/bin/env python3
"""Conan consumer test for tracexec 0.17.0 (Rust binary package).

Two layers of verification:

  1. package integrity — the packaged `tracexec` executable exists;
  2. consumer smoke + HarmonyOS traits — test_tracexec.py runs the binary,
     asserts AArch64 / musl loader / OHOS code signature, exercises the real
     CLI (`--version` / `--help` / `generate-completions` / error handling)
     and probes the tracing entry point tolerantly (on stock OHOS the kernel
     denies unprivileged ptrace with EPERM; where tracing is permitted the
     test instead asserts a successful trace).
"""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class TracexecTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"
    exports_sources = "test_tracexec.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        package_folder = self.dependencies["tracexec"].package_folder
        exe = os.path.join(package_folder, "bin", "tracexec")
        if not os.path.isfile(exe):
            raise AssertionError(f"Missing tracexec executable: {exe}")

        if not can_run(self):
            self.output.info("Cross-building: verified package layout only.")
            return

        script = os.path.join(self.source_folder, "test_tracexec.py")
        result = self.run(
            f'PACKAGE_FOLDER="{package_folder}" "{sys.executable}" "{script}"',
            env="conanrun",
            ignore_errors=True,
        )
        if result != 0:
            raise AssertionError(
                f"tracexec test_package failed with exit code {result}"
            )
