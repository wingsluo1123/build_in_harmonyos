#!/usr/bin/env python3
"""Conan recipe — xeus 5.0.0 (Jupyter kernel protocol C++ library, HarmonyOS PC aarch64 适配).

xeus 是 Jupyter 内核协议参考库（CMake 构建，C++17），本配方：

依赖:
- nlohmann_json/3.12.0  （公开头 xjson.hpp 依赖，xeusConfig 要求 EXACT 匹配）
- libuuid/2.42.2        （UNIX 下 xguid 的 UUID 生成，FindLibUUID）

OHOS 适配:
- CMake 无法识别 OHOS（"System is unknown to cmake"），按仓库通行做法把
  CMAKE_SYSTEM_NAME 归一为 Linux、arch=aarch64，避免 CMake 探测失败；
- 测试（XEUS_BUILD_TESTS）默认关闭：上游 51 个独立 TEST_CASE 已在本任务
  逐项枚举并实际构建运行（见 reports/test-ledger.md），不占配方构建产物；
- 产物为静态库 libxeus.a 与公开头 include/xeus/*.hpp（R26 系统同名库规则
  不适用于本库，默认静态编排由 Conan 依赖链管理）。

本处方不注入共享系统前缀（R49），也不通过编译选项注入平台宏（R8/PF5）。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class XeusConan(ConanFile):
    name = "xeus"
    version = "5.0.0"
    description = "xeus 5.0.0 — Jupyter kernel protocol C++ library"
    license = "BSD-3-Clause"
    homepage = "https://github.com/jupyter-xeus/xeus"
    url = "https://github.com/jupyter-xeus/xeus"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("nlohmann_json/3.12.0")
        if self.settings.os in ("Linux", "OHOS"):
            self.requires("uuid/2.40.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)
        # OHOS 平台归一化: CMake 无 HarmonyOS 平台模块，归一为 Linux
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        tc.cache_variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.cache_variables["XEUS_BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.cache_variables["XEUS_BUILD_STATIC_LIBS"] = "OFF" if self.options.shared else "ON"
        tc.cache_variables["XEUS_BUILD_TESTS"] = "OFF"
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
        # xeusConfig.cmake 会 find_dependency(nlohmann_json EXACT) 与 LibUUID
        self.cpp_info.libs = ["xeus"]
        self.cpp_info.includedirs = ["include"]
        # 公开头 xjson.hpp/xhelper.hpp 直接 include nlohmann/json.hpp，
        # 静态库链接 libuuid → 消费者必须透传这两个依赖的 include/lib 路径
        requires = ["nlohmann_json::nlohmann_json"]
        if self.settings.os in ("Linux", "OHOS"):
            requires.append("uuid::uuid")
        self.cpp_info.requires = requires