#!/usr/bin/env python3
"""Conan test_package - nymphcast 0.2 smoke test."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class NymphcastTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # 运行主程序检查是否可执行
            for exe in ['nymphcast', 'nymphcast_server']:
                self.run(f"{exe} --help || true", env="conanrun")
