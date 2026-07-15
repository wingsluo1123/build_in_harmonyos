#!/usr/bin/env python3
"""Conan test_package for scsi-tgt v1.0 — binary tool smoke test.

Verifies that the tgtd binary is installed and runs correctly.
R34: test executes the package's binary (tgtd --version).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class ScsiTgtTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R32: Platform check — only run on Linux/OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            return

        if not can_run(self):
            return

        # Get the tgtd binary path from the dependency package
        tgtd_bin = os.path.join(
            self.dependencies["scsi-tgt"].package_folder, "bin", "tgtd"
        )

        # Verify binary exists
        assert os.path.isfile(tgtd_bin), f"tgtd binary not found at {tgtd_bin}"

        # Run smoke test: tgtd --version should output version string
        self.run(f'"{tgtd_bin}" --version', env="conanrun")
