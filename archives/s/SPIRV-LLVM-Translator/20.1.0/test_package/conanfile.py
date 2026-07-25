#!/usr/bin/env python3
"""Conan test_package — spirv-llvm-translator 20.1.0

L1 测试：运行 llvm-spirv 二进制验证包完整性 (R34: 执行被测包的二进制)。
"""
from conan import ConanFile
from conan.tools.cmake import cmake_layout


class SpirvLlvmTranslatorTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def test(self):
        # 执行被测包的二进制 (R34): 运行 llvm-spirv 验证可执行性
        # conanrun 环境设置 LD_LIBRARY_PATH 和 PATH 指向包的 bin/lib 目录
        self.run("llvm-spirv --help", env="conanrun")
