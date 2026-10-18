#!/usr/bin/env python3
"""Conan test_package for totem-pl 3.26.7 — 消费者用例（C API 实质调用验证）。

R34: test() 必须实质调用被测包 API。CMake 方式（同 libgee/glib 先例）：
CMakeDeps 通过组件 requires 传递 glib/libxml2 依赖，test.c 模拟业务上层
（如 totem 播放器）：写临时 m3u → totem_pl_parser_new → 连接 entry-parsed
信号 → totem_pl_parser_parse 解析 file:// URI → 断言结果/条目数/首条目 location。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TotemPlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # test.c calls glib APIs directly (GHashTable, g_signal, gio URI helpers)
        self.requires("glib/2.84.0.2")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 直接运行测试二进制（conanrun 环境注入 LD_LIBRARY_PATH）
        self.run("./test_package", env="conanrun")
