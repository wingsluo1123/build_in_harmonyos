#!/usr/bin/env python3
"""Conan consumer integration test for the pure Python kitchen package."""
import os
import shutil

from conan import ConanFile


class KitchenTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_python = self.dependencies["kitchen"].package_folder
        bash = self._find_bash()
        self.run(
            f'PYTHONPATH="{package_python}" "{bash}" test.sh',
            env="conanrun",
        )

    def _find_bash(self):
        candidates = [
            os.environ.get("CONFIG_SHELL"),
            shutil.which("bash"),
            "/data/service/hnp/bin/bash",
            "/bin/bash",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        raise RuntimeError("bash executable is required to run the kitchen test_package")
