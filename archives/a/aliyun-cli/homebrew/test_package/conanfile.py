#!/usr/bin/env python3
"""Conan test_package for aliyun-cli homebrew (v3.0.229)."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class AliyunCliTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["aliyun-cli"].package_folder
        bin_path = os.path.join(package_folder, "bin", "aliyun")
        assert os.path.isfile(bin_path), f"aliyun binary not found: {bin_path}"

        if can_run(self):
            test_script = os.path.join(self.recipe_folder, "test.sh")
            self.run(
                f'bash "{test_script}" "{bin_path}"',
                env="conanrun",
            )
        else:
            with open(bin_path, "rb") as binary:
                magic = binary.read(4)
            assert magic == b"\x7fELF", f"aliyun is not an ELF binary: {magic!r}"
            self.output.info(
                f"aliyun binary exists and has ELF magic: {bin_path}"
            )
