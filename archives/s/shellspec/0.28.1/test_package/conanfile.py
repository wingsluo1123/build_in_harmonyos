#!/usr/bin/env python3
"""Conan test_package for shellspec 0.28.1 — Shell script test.

Verifies that the shellspec command is functional after installation.
Runs `shellspec --version` and a minimal spec file.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class ShellspecTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            dep = self.dependencies["shellspec"]
            bin_dir = os.path.join(dep.package_folder, "bin")
            shellspec_cmd = os.path.join(bin_dir, "shellspec")

            # Find sh for executing the scripts (OHOS has /bin/sh)
            sh_path = shutil.which("sh") or "/bin/sh"

            # Run test.sh smoke test (source file for CI L0c compliance)
            self.run(
                f'cd "{self.source_folder}" && '
                f'PATH="{bin_dir}:$PATH" '
                f'"{sh_path}" test.sh',
                env="conanrun"
            )

            # Test 1: shellspec --version should output 0.28.1
            self.run(f'PATH="{bin_dir}:$PATH" "{shellspec_cmd}" --version', env="conanrun")
