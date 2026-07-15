#!/usr/bin/env python3
"""Conan test_package — mkinitfs 3.4.5

Tests that the mkinitfs tool is installed and can show help output.
mkinitfs is a shell script tool, so we test by running it directly.
"""
import os

from conan import ConanFile


class MkinitfsTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find mkinitfs binary in the package's sbin directory
        dep = self.dependencies["mkinitfs"]
        bin_dir = os.path.join(dep.package_folder, "usr", "sbin")
        mkinitfs = os.path.join(bin_dir, "mkinitfs")

        # Verify mkinitfs binary exists (L1e will sabotage this)
        assert os.path.exists(mkinitfs), f"mkinitfs binary not found at {mkinitfs}"
        assert os.path.getsize(mkinitfs) > 0, "mkinitfs is empty"

        # Set TMPDIR for OHOS (E002: /tmp is read-only)
        tmpdir = os.path.expanduser("~/tmp")
        os.makedirs(tmpdir, exist_ok=True)

        # Run mkinitfs -h and check output contains "usage"
        # mkinitfs -h exits with code 1 on OHOS, so pipe to grep
        # Exit code comes from grep (0=found, 1=not found)
        # If binary is removed, shell fails to find it → grep fails → test fails (L1e)
        self.run(
            f'TMPDIR={tmpdir} "{mkinitfs}" -h 2>&1 | grep -q usage',
            env="conanrun"
        )
