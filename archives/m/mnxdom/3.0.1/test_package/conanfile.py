#!/usr/bin/env python3
"""Conan test_package — mnxdom 3.0.1（消费者视角验证）。

编译并运行一个真实调用 mnxdom API 的消费者程序（R34）：
经 CMakeDeps 生成的 mnxdom 配置完成 find_package + 链接，
程序内部构建 MNX 文档、调用 schemaValidate()（经由 json-schema-validator）、
落盘并重新加载。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class MnxdomTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # mnxdom 的公共头会 #include <nlohmann/json.hpp>；CMakeDeps 不会为
        # 「无组件」的依赖自动生成 find_dependency，消费端必须显式 require
        # 该 header-only 依赖才能拿到它的 include 目录（同仓库
        # json-schema-validator 的 test_package 处理方式一致）。
        self.requires("nlohmann_json/3.12.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "bash")
        # 本包默认静态交付（libmnxdom.a），运行期本不需要额外搜索路径；
        # 仍显式带上 conanrun，切到共享形态（-o mnxdom/*:shared=True）时同样可用。
        self.run(f'{bash} -c "./test_mnxdom"', cwd=self.cpp.build.bindirs[0], env="conanrun")
