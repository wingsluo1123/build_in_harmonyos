#!/usr/bin/env python3
"""mgclient 1.8.0 Conan 配方 — CMake 构建系统。

mgclient 是 Memgraph 数据库的 C 语言客户端库（含可选 C++ 绑定）。
基于 C11，依赖 OpenSSL（TLS/加密）。
构建方式：按选项构建共享/静态库，默认静态（R26 系统同名库约束
——mgclient 非系统同名库，但保持静态默认以便消费者稳定链接）。
许可证：MIT
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class MgclientConan(ConanFile):
    name = "mgclient"
    version = "1.8.0"
    description = "C client library for Memgraph database (Bolt protocol)"
    license = "MIT"
    homepage = "https://github.com/memgraph/mgclient"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6")

    def validate(self):
        # R32：平台检测必须使用 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"OS {self.settings.os} not supported, requires Linux or OHOS"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33：所有标志来自 Conan 工具链，不使用 shell 环境变量
        deps = CMakeDeps(self)
        # 上游 src/CMakeLists.txt 使用 find_package(OpenSSL REQUIRED)
        # 和 OPENSSL_LIBRARIES/OPENSSL_INCLUDE_DIR 传统变量，但本地
        # OpenSSL conan 配方未定义组件。通过 CMakeDeps 属性映射，
        # 使生成的 CMake 目标与上游期望的名称匹配。
        deps.set_property("openssl", "cmake_file_name", "OpenSSL")
        deps.generate()
        tc = CMakeToolchain(self)
        # 上游 CMakeLists.txt 在 OHOS 平台识别：补丁已加入
        # OHOS/HarmonyOS 分支。本机 OHOS 适配版 conan 未自动生成
        # CMAKE_SYSTEM_NAME（"System is unknown to cmake"），显式
        # 注入 HarmonyOS，使上游走 Linux/POSIX 分支。
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_SYSTEM_NAME"] = "HarmonyOS"
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            # CMake 无 HarmonyOS 平台模块（Platform/HarmonyOS.cmake
            # 不存在），CMAKE_SHARED_LIBRARY_SONAME_<LANG>_FLAG 未定义，
            # SOVERSION 无法转成 DT_SONAME（L5 门禁失败）。CMake 实际
            # 消费的是语言后缀变量（Linux.cmake:6 定义 C 语言版本），
            # 显式注入与 Linux 一致的链接标志，恢复 SONAME 生成。
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_FLAG"] = "-Wl,-soname,"
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # R9：OHOS worker 并行约束，单任务构建
        cmake.build(cli_args=["--parallel", "1"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 复制许可证文件
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "mgclient")
        self.cpp_info.set_property("cmake_target_name", "mgclient::mgclient")
        self.cpp_info.set_property("pkg_config_name", "mgclient")
        self.cpp_info.libs = ["mgclient"]
        self.cpp_info.requires = ["openssl::openssl"]
