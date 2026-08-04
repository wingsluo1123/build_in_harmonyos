#!/usr/bin/env python3
"""Conan recipe for liquid-dsp v1.8.0 — CMake project (pure C signal processing math library).

No external dependencies (pure math). MIT license.
Built as static library for OHOS.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LiquiddspConan(ConanFile):
    name = "liquid-dsp"
    version = "1.8.0"
    description = "liquid-dsp is a free and open-source signal processing library for software-defined radios"
    license = "MIT"
    homepage = "https://liquidsdr.org"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_STATIC_LIBS"] = "OFF" if self.options.shared else "ON"
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        tc.variables["BUILD_AUTOTESTS"] = "ON"    # 上游 autotest 1341 项，CI 中实际编译运行
        tc.variables["BUILD_BENCHMARKS"] = "OFF"
        tc.variables["BUILD_SANDBOX"] = "OFF"
        tc.variables["BUILD_DOC"] = "OFF"
        tc.variables["ENABLE_SIMD"] = "OFF"
        tc.variables["FIND_SIMD"] = "OFF"
        tc.variables["FIND_FFTW"] = "OFF"
        tc.variables["FIND_THREADS"] = "OFF"
        tc.variables["ENABLE_LOGGING"] = "ON"     # autotest 依赖 logging 符号
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 运行上游 autotest 套件（1341 项测试），CI 构建中可复现
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["liquid"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "liquid-static")
        self.cpp_info.set_property("cmake_target_name", "liquid::liquid-static")
        self.cpp_info.set_property("pkg_config_name", "liquid-dsp")
