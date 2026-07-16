#!/usr/bin/env python3
"""Test package for txt2man 1.7.1"""
import os

from conan import ConanFile


class Txt2ManTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_dir = self.dependencies["txt2man"].cpp_info.bindirs[0]
        txt2man_cmd = os.path.join(bin_dir, "txt2man")

        test_script = os.path.join(self.source_folder, "test_txt2man.sh")
        self.run(f'sh "{test_script}" "{txt2man_cmd}"', env="conanrun")
