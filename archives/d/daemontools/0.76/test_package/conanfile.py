#!/usr/bin/env python3
"""Conan test_package for daemontools 0.76.

Verifies that daemontools binaries are installed and functional.
Tests tai64n/tai64nlocal timestamp conversion and envdir environment
variable handling — exercising actual binary behavior (R34).
"""
import os

from conan import ConanFile


class DaemontoolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R32: Platform check — only run on Linux/OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            return

        # Get the daemontools binary directory from the dependency package
        pkg_folder = self.dependencies["daemontools"].package_folder
        bin_dir = os.path.join(pkg_folder, "bin")

        # Verify key binaries exist
        for binary in ("tai64n", "tai64nlocal", "envdir", "svstat"):
            binary_path = os.path.join(bin_dir, binary)
            assert os.path.isfile(binary_path), f"{binary} not found at {binary_path}"

        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution (R5: OHOS has no /bin/sh)
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'BIN_DIR="{bin_dir}" {bash} test.sh', env="conanrun")
