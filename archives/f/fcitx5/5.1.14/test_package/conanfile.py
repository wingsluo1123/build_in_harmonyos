#!/usr/bin/env python3
"""Conan test_package — fcitx5 消费者验证。

真实消费者视角：仅通过已安装/导出的公开头文件与 CMake 目标使用本库。
调用 Fcitx5::Utils 的公开 API（SemanticVersion 解析、Key 字符串构造、
stringutils::trim）并断言可观察结果；链接 Fcitx5::Core 验证核心库可链接。

OHOS 运行时要点：OHOS 加载器拒绝加载 RUNPATH 指向 conan 缓存目录的库
（dlopen 报 "Permission denied"，本机实测）；库与 test 二进制均不写
RUNPATH（保持 conan 默认 CMAKE_SKIP_RPATH=1），运行时依赖解析交给
conanrun 环境（LD_LIBRARY_PATH 指向被测包与 libuv/gettext 的 lib 目录，
本机实测可正常加载）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Fcitx5TestConan(ConanFile):
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
        # 消费者真实运行：用 conanrun 环境（LD_LIBRARY_PATH 含被测包与
        # libuv/gettext 的 lib）直接运行二进制。ctest 不继承 conanrun，
        # 且 OHOS 加载器拒绝缓存路径 RUNPATH，故不走 cmake.test()。
        bindir = self.cpp.build.bindirs[0]
        self.run(os.path.join(bindir, "test_fcitx5"), env="conanrun")
        self.run(os.path.join(bindir, "test_fcitx5_ohos"), env="conanrun")