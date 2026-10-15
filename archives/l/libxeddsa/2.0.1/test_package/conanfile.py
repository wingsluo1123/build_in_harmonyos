#!/usr/bin/env python3
"""Conan test_package for libxeddsa 2.0.1 — 消费者 + OHOS 专项实质测试。

test() 通过 cmake.test() 运行两个 CTest 用例:
  1. test_libxeddsa      — 消费者: xeddsa_init/seed_to_ed25519_pub/
                           ed25519_seed_sign/ed25519_verify（含篡改消息负例）
  2. ohos_specific_test  — OHOS 专项: 随机源探测/公钥转换往返/x25519/签名验签
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
import os


class LibxeddsaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
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
        cmake = CMake(self)
        cmake.test()
        # 直接运行消费者测试二进制（实质执行被测库 API，满足 L0d/R34）
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_libxeddsa"), env="conanrun")
