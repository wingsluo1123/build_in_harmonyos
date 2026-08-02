#!/usr/bin/env python3
"""Conan test_package for unxip."""
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.files import copy


class UnxipTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        if self.source_folder != self.build_folder:
            copy(self, "test.sh", src=self.source_folder, dst=self.build_folder)

    def test(self):
        package_folder = self.dependencies["unxip"].package_folder
        bin_dir = os.path.join(package_folder, "bin")
        shell = self._test_shell()
        test_script = os.path.join(self.build_folder, "test.sh")
        self.run(f'PATH="{bin_dir}:$PATH" {shlex.quote(shell)} {shlex.quote(test_script)}', env="conanrun")

    def _test_shell(self):
        for candidate in (
            os.environ.get("CONFIG_SHELL"),
            shutil.which("bash"),
            "/storage/Users/currentUser/usr/local/bin/bash",
            "/data/service/hnp/bin/bash",
            shutil.which("sh"),
            "/system/bin/sh",
            "/bin/sh",
        ):
            if candidate and os.path.isfile(candidate):
                return candidate
        return "sh"
