#!/usr/bin/env python3
"""Conan recipe for libzippp 7.1 — C++ wrapper for libzip.

CI 的唯一构建输入。conan create 读取此文件完成构建。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibzipppConan(ConanFile):
    name = "libzippp"
    version = "7.1"
    description = "C++ wrapper for libzip — object-oriented ZIP archive manipulation"
    license = "BSD-2-Clause"
    homepage = "https://github.com/ctabin/libzippp"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libzip/1.10.1@ohpcd/stable")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["LIBZIPPP_INSTALL"] = "ON"
        tc.variables["LIBZIPPP_INSTALL_HEADERS"] = "ON"
        tc.variables["LIBZIPPP_BUILD_TESTS"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["libzippp_static"]
        self.cpp_info.requires = ["libzip::libzip"]
