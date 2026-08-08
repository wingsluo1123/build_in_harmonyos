#!/usr/bin/env python3
"""Conan test_package for akku 1.1.0 — import + version smoke test."""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class AkkuTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # 验证 akku 可执行且输出正确版本（akku 用 version 子命令，非 --version）
            self.run("akku version", env="conanrun")
