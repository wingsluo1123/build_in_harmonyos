#!/usr/bin/env python3
"""Conan test_package — rofi 2.0.0 消费者用例

消费者用例（R34）：模拟上层组件调用 rofi 公开 CLI（rofi -v 版本探针），
验证调用路径的编译/链接/运行。rofi 为纯 CLI 应用（无对外可链接库），
test() 实际执行被测包二进制（经消费者程序 popen 调用 rofi -v 并断言退出码与输出）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class RofiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # 显式声明 run/build 环境生成器：rofi 运行需宿主依赖库（wayland/glib 等）
    # 的 LD_LIBRARY_PATH 与包内 bin/ 的 PATH（2048.c 等仓内先例；仅声明 CMake 系
    # 生成器会覆盖默认环境生成器，导致 env="conanrun" 无脚本可载）
    generators = "CMakeDeps", "CMakeToolchain", "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 运行消费者程序：内部 popen("rofi -v") 调用被测包二进制，
        # 断言退出码 0 且输出含 "Version"（实测输出 "Version: 2.0.0"，无需显示环境）
        exe = os.path.join(self.cpp.build.bindirs[0], "test_rofi")
        self.run(exe, env="conanrun")
