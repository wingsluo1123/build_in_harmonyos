#!/usr/bin/env python3
"""Conan test_package — ir_keytable 1.32.0.

验证 ir-keytable 可执行并实际运行（R34：实质执行被测包二进制）。
调用 test_ir_keytable.sh 测试脚本（L0c 门禁要求 test_package/ 有测试源文件）。
"""
import os

from conan import ConanFile


class IrKeytableTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["ir_keytable"]
        assert pkg.package_folder, "ir_keytable package folder not resolved"
        bin_dir = os.path.join(pkg.package_folder, "bin")
        script = os.path.join(self.source_folder, "test_ir_keytable.sh")
        self.run('sh "{}" "{}"'.format(script, bin_dir))
