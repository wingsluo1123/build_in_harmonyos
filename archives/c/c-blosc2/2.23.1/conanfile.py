#!/usr/bin/env python3
"""Conan recipe — c-blosc2 2.23.1.

c-blosc2 是高性能压缩二进制数据存储库，blosc 的第二代实现。
构建系统: CMake
依赖: lz4 + zstd + zlib-ng-compat (Conan 管理)
"""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import get, copy
import os


class CBlosc2Conan(ConanFile):
    name = "c-blosc2"
    version = "2.23.1"
    description = "Fast, compressed, persistent binary data store library for C"
    license = "BSD-3-Clause"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    homepage = "https://www.blosc.org"
    topics = ("compression", "binary", "persistent", "blosc")
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def requirements(self):
        self.requires("lz4/1.10.0")
        self.requires("zstd/1.5.7")
        self.requires("zlib-ng-compat/2.3.3")

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.get_safe("fPIC", True))
        tc.variables["BUILD_TESTS"] = False
        tc.variables["BUILD_FUZZERS"] = False
        tc.variables["BUILD_BENCHMARKS"] = False
        tc.variables["BUILD_EXAMPLES"] = False
        tc.variables["BUILD_PLUGINS"] = False
        tc.variables["PREFER_EXTERNAL_LZ4"] = True
        tc.variables["PREFER_EXTERNAL_ZLIB"] = True
        tc.variables["PREFER_EXTERNAL_ZSTD"] = True
        if self.settings.os == "OHOS":
            arch_map = {
                "armv8": "aarch64",
                "armv8.1": "aarch64",
                "armv8.2": "aarch64",
                "armv8.3": "aarch64",
                "armv8.4": "aarch64",
                "armv8.5": "aarch64",
                "armv8.6": "aarch64",
                "armv8.7": "aarch64",
                "armv8.8": "aarch64",
                "armv8.9": "aarch64",
            }
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = arch_map.get(
                str(self.settings.arch), str(self.settings.arch))
        tc.generate()
        # CMakeDeps: 生成 find_package 配置文件，让 c-blosc2 上游 CMakeLists.txt 的
        # find_package(LZ4/ZSTD/ZLIB_NG) 能定位到 Conan 管理的依赖。
        # 缺少 CMakeDeps 时 find_package 全部失败 → fallback find_library 只找到 .a
        # 但未设置 include 目录 → 编译 blosc2.c 时 fatal error: 'lz4.h' file not found。
        deps = CMakeDeps(self)
        # c-blosc2 CMakeLists.txt 调用 find_package(LZ4) 并检查 TARGET LZ4::lz4
        deps.set_property("lz4", "cmake_file_name", "LZ4")
        deps.set_property("lz4", "cmake_target_name", "LZ4::lz4")
        # zstd recipe 已设置 cmake_file_name="zstd" + cmake_target_name="zstd::libzstd"，
        # 与 c-blosc2 的 find_package(ZSTD) + TARGET zstd::libzstd 匹配，无需覆盖。
        # c-blosc2 CMakeLists.txt 调用 find_package(ZLIB_NG) 并检查 TARGET zlib-ng::zlib
        deps.set_property("zlib-ng-compat", "cmake_file_name", "ZLIB_NG")
        deps.set_property("zlib-ng-compat", "cmake_target_name", "zlib-ng::zlib")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["blosc2"]
