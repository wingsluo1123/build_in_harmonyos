#!/usr/bin/env python3
"""Conan test_package — relic 0.5.0 消费者测试（L1）。

以**库使用者**身份从安装好的包编译、链接并真实调用 relic 公开 API，
用断言决定退出码（不是只 include / 只链接 / 只打印）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class RelicTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if self.conf.get("tools.build:skip_test", default=False):
            return
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_relic_consumer")
        # 默认静态包：产物只有 .a，链接进可执行文件、无运行期装载依赖。
        # shared=True 包需把包内 lib 目录放进动态加载搜索路径（该包不带
        # SONAME，DT_NEEDED 记的是裸 librelic.so）。
        dep = self.dependencies["relic"]
        dep_libdir = os.path.join(dep.package_folder, "lib")
        cmd = 'export LD_LIBRARY_PATH="%s:${LD_LIBRARY_PATH:-}"; %s' % (
            dep_libdir, bin_path)
        self.run(cmd, env="conanrun")
