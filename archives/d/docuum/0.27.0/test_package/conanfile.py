#!/usr/bin/env python3
"""Conan test_package for docuum 0.27.0 — verifies the failed-adaptation record."""

import os
import sys

from conan import ConanFile


class DocuumTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_failed_archive.py")
        # R34: check=True 使测试脚本非零退出时 test_package 正确失败，
        # 避免断言失败仍被 Conan 判定通过（AI review P1）
        self.run(f'"{sys.executable}" "{script}" "{package_folder}"', check=True)
