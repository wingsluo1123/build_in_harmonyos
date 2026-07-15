#!/usr/bin/env python3
"""Conan test_package for massdns — verifies the installed binary works.

R34: test must substantially depend on the tested package.
We run `massdns --version` to verify the binary is functional.
"""
import os

from conan import ConanFile


class MassdnsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R32: Platform check — only run on Linux/OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            return

        # Get the massdns binary path from the dependency package
        massdns_bin = os.path.join(
            self.dependencies["massdns"].package_folder, "bin", "massdns"
        )

        # Verify binary exists
        assert os.path.isfile(massdns_bin), f"massdns binary not found at {massdns_bin}"

        # Run smoke test — massdns --version outputs "massdns" and exits 0
        self.run(f'"{massdns_bin}" --version', env="conanrun")
