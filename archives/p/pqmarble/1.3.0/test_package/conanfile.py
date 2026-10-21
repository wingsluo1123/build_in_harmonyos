#!/usr/bin/env python3
"""Conan test_package for pqmarble 1.3.0.

R34: 必须实质调用被测包 API —— 测试程序调用 Marble 的 GType 注册、
marble_get_css_provider_for_data()，并额外做鸿蒙特有断言（产物 ELF 为
aarch64 + OHOS ABI note）。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PqmarbleTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps", "PkgConfigDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        self.tool_requires("pkgconf/3.0.6")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self.run("./test_pqmarble", env="conanrun")
