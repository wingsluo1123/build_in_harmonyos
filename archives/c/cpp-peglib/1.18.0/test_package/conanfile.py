#!/usr/bin/env python3
"""test_package — cpp-peglib 1.18.0 消费者验证

  * test_package.cpp —— 真编译真链接交付的 peglib.h，10 项判据（版本宏、
    字面量语法、算术求值动作/优先级/括号、token 分隔语法、错误定位回调、
    parse(input,val) 语义值）。
  * test_layout.py   —— 交付形态自检（M1..M8，header-only 口径）。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class CppPeglibTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
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
        if not can_run(self):
            raise Exception("cannot run the consumer test on this host")
        test_binary = os.path.join(self.cpp.build.bindirs[0], "test_package")
        if not os.path.isfile(test_binary):
            raise Exception("consumer test binary not found: {}".format(test_binary))
        self.run('"{}"'.format(test_binary), env="conanrun")

        ref = self.dependencies["cpp-peglib"]
        self.run('python3 "{}" --package-folder "{}" --os "{}" --arch "{}" '
                 '--version "{}"'.format(
                     os.path.join(self.source_folder, "test_layout.py"),
                     ref.package_folder, self.settings.os, self.settings.arch,
                     ref.ref.version),
                 env="conanrun")
