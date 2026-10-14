#!/usr/bin/env python3
"""test_package for tuning 1.1.0 — Conan 层 2 消费者验证。

两个测试可执行文件（经 ctest 运行）：
  * test_tuning.cpp           —— 消费者视角真实 API（SCL/KBM 解析、频率映射、错误路径）
  * test_tuning_harmonyos.cpp —— **鸿蒙特有测试**（OHOS aarch64 平台 + OHOS libc/文件系统/locale 集成）
"""
import json
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class TuningTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake 不识别 HarmonyOS 目标平台，与包配方保持一致映射到 Linux/aarch64
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        elif self.settings.os == "Linux":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_pkg = {
            "executed": True,
            "passed": False,
            "command": "ctest --output-on-failure",
            "discovered": 2,
            "passedCount": 0,
        }
        if cross_building(self):
            test_pkg["skipped"] = "cross-building"
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
            return
        # OHOS: /system/bin/sh (mksh) 不能直接 exec ELF，用构建环境的 bash 包装
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        try:
            self.run(f'{bash} -c "ctest --output-on-failure"', env="conanrun")
        except Exception:
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
            raise
        test_pkg["passed"] = True
        test_pkg["passedCount"] = 2
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
