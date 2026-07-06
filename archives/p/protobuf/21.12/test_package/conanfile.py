#!/usr/bin/env python3
"""Conan test_package for protobuf 21.12 — Conan L1 official test.

测试策略：
- person.pb.cc / person.pb.h 由 protoc 预生成（构建时已验证 protoc --version）
- test_package 聚焦验证 libprotobuf 库功能：序列化/反序列化、repeated 字段、默认值、字段清空
- OHOS 平台限制：Conan cache 中的 protoc 未签名无法执行 (R7/ELF签名)，
  因此 proto 代码预生成后随 test_package 一起分发

Tests:
1. test_protobuf: 5 个子测试覆盖核心 protobuf C++ API
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ProtobufTestConan(ConanFile):
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
        # OHOS: /system/bin/sh (mksh) 无法直接执行 ELF，用 bash 包装
        bash = shutil.which("bash")
        test_bin = os.path.join(self.cpp.build.bindir, "test_protobuf")
        if bash:
            self.run(f"'{bash}' -c '{test_bin}'", env="conanrun")
        else:
            self.run(test_bin, env="conanrun")
