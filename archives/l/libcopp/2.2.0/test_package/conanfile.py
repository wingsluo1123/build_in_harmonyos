#!/usr/bin/env python3
"""Conan test_package — libcopp 2.2.0.

真实编译并运行一次协程上下文切换（create/start/yield/resume/ret_code）。
这条路径必须经过打包进产物的 **arm64 fcontext 汇编**，因此它同时验证：
  ① 头文件与静态库正确交付；
  ② 打包进去的确实是 arm64/aapcs/elf/gas 上下文切换实现（而不是被上游
     `unknown => x86_64` 误选的 x86_64 汇编）；
  ③ 该实现在 OHOS 上真的能切换栈并取回返回码。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibcoppTestConan(ConanFile):
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
            self.output.warn("Skip run test on cross-built package")
            return
        cmd = os.path.join(self.cpp.build.bindirs[0], "test_libcopp")
        self.run(cmd, env="conanrun")
