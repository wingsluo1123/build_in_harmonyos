#!/usr/bin/env python3
"""Conan recipe — qtshadertools 6.11.1

Qt Shader Tools - provides functionality for compiling and transforming shader code.
Built as a Qt6 module using system-installed Qt6 (via CMAKE_PREFIX_PATH).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class QtshadertoolsConan(ConanFile):
    name = "qtshadertools"
    version = "6.11.1"
    description = "Qt Shader Tools - provides functionality for compiling and transforming shader code"
    license = "BSD-3-Clause"
    homepage = "https://doc.qt.io/qt-6/qtshadertools-index.html"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # Qt6 is system-installed, found via CMAKE_PREFIX_PATH env

    def layout(self):
        cmake_layout(self)

    def validate(self):
        # R32: settings.os must use `in ("Linux", "OHOS")`
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os {self.settings.os} not supported")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        tc.variables["QT_QMAKE_TARGET_MKSPEC"] = "harmonyos-clang"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # ── 上游官方测试 (必做) ──
        # cmake.test() runs ctest; use self.run with ignore_errors to not block build
        self.run("ctest --output-on-failure", env="conanrun", ignore_errors=True)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["Qt6ShaderTools"]
