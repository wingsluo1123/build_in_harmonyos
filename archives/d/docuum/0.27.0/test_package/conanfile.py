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
        # R34: Conan 2.x self.run() 不支持 check 参数，改用返回码检查，
        # 使测试脚本非零退出时 test_package 正确失败（避免断言失败仍被判通过）
        rc = self.run(f'"{sys.executable}" "{script}" "{package_folder}"')
        if rc != 0:
            raise Exception(f"test_failed_archive.py exited with code {rc}")
