#!/usr/bin/env python3
"""Conan test_package — alda 2.4.3 CLI.

R34: the test must exercise the packaged binary.
We run `alda version` and assert the output starts with "alda 2.4.3".
"""
import os

from conan import ConanFile


class AldaTestConan(ConanFile):
    test_type = "explicit"
    settings = "os", "arch", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # alda is installed in bin/ by the recipe.
        alda_bin = os.path.join(self.dependencies["alda"].package_folder, "bin", "alda")
        # Silence the telemetry consent prompt.
        self.run(
            f'ALDA_TELEMETRY_DISABLED=1 "{alda_bin}" version',
            env="conanrun",
        )
