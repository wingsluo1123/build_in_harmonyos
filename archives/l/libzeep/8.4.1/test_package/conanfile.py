#!/usr/bin/env python3
"""Conan test_package — libzeep 8.4.1 consumer smoke test.

通过公共 API zeep::uri 解析 RFC3986 URI，并调用 zeep::el::value JSON
解析，验证库头文件、链接与运行正常（R34：实质调用被测包 API）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import can_run


class LibzeepTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            cmd = os.path.join(self.cpp.build.bindirs[0], "test_package")
            self.run(cmd, env="conanrun")
            # 鸿蒙专项测试（真实 HTTP daemon 往返 + URI/JSON 公开 API）
            ohos_cmd = os.path.join(self.cpp.build.bindirs[0], "ohos_test")
            self.run(ohos_cmd, env="conanrun")
            # 消费者用例（独立于上游测试/鸿蒙专项测试，仅公开 API 模拟业务组件）
            consumer_cmd = os.path.join(self.cpp.build.bindirs[0], "consumer_app")
            self.run(consumer_cmd, env="conanrun")
