#!/usr/bin/env python3
"""Conan test_package — mfiutil 1.0.15-rivoreo-r2-rc-20250214-e8c6289 (MegaRAID management CLI, executable).

test.sh drives the packaged mfiutil binary WITHOUT requiring real MegaRAID
hardware: `version` (pure userland), the no-args usage path, the unknown
command error path, and the device-open failure path (no
/dev/megaraid_sas_ioctl_node on a machine without the megaraid_sas
driver) which exercises the Linux ioctl code path end-to-end.

HMBS_TEST_PACKAGE_RESULT is emitted by test.sh as machine evidence.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class MfiutilTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["mfiutil"].package_folder
        bin_path = os.path.join(package_folder, "usr", "sbin", "mfiutil")
        assert os.path.isfile(bin_path), f"mfiutil binary not found: {bin_path}"

        if can_run(self):
            test_script = os.path.join(self.recipe_folder, "test.sh")
            shell = os.environ.get("SHELL", "/bin/sh")
            cwd = os.environ.get("TMPDIR") or os.environ.get("TMP") or self.recipe_folder
            self.run(f'"{shell}" "{test_script}" "{bin_path}"', cwd=cwd)
            # HMBS_TEST_PACKAGE_RESULT emitted by test.sh.
        else:
            with open(bin_path, "rb") as binary:
                magic = binary.read(4)
            assert magic == b"\x7fELF", f"mfiutil is not an ELF binary: {magic!r}"
            self.output.info(f"mfiutil binary exists and has ELF magic: {bin_path}")
