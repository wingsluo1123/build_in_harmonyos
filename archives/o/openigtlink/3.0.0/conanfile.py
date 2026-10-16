#!/usr/bin/env python3
"""Conan recipe — openigtlink 3.0.0 (CMake)

OpenIGTLink is a network communication protocol and library for image-guided
therapy and medical robotics.  The library has no third-party dependencies: it
only needs POSIX threads, libm and the socket API, all provided natively by the
OHOS sysroot.

Upstream test suite (Testing/, CTest) is built and executed inside build():
upstream registers 63 ADD_TEST statements, one of which duplicates the name
igtlPositionMessageTest, so CTest exposes 62 unique cases.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class OpenigtlinkConan(ConanFile):
    name = "openigtlink"
    version = "3.0.0"
    description = "Network communication protocol and library for image-guided therapy and medical robotics"
    license = "BSD-3-Clause"
    homepage = "https://openigtlink.org/"
    url = "https://github.com/openigtlink/OpenIGTLink"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 零第三方依赖：仅 POSIX 线程 / libm / socket 族，由 OHOS sysroot 原生提供。
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 动态/静态由 Conan 选项驱动；本库非系统同名库，默认动态由 Conan 管理依赖链。
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        tc.variables["BUILD_DOCUMENTATION"] = "OFF"
        # 上游 cmake_minimum_required(VERSION 2.4) 与 CMake 4.x 不兼容（< 3.5 已移除兼容层）。
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # 上游安装目录默认为 lib/igtl 与 include/igtl，改为 Conan 标准布局。
        tc.variables["OpenIGTLink_INSTALL_LIB_DIR"] = "lib"
        tc.variables["OpenIGTLink_INSTALL_INCLUDE_DIR"] = "include"
        # ── 上游官方测试套件（测试体系层 1）──
        tc.variables["BUILD_TESTING"] = "ON"
        # USE_GTEST=OFF 使用上游 igtlTestConfig.h.in 内置的非-gtest 回退 runner：
        # 默认的 USE_GTEST=ON 会在 configure 期用 ExternalProject 下载
        # googletest/googlemock release-1.7.0（2016 年产物），把网络依赖带进构建期；
        # 回退路径下 ADD_TEST 注册面与用例数完全不变（63 条语句 / 62 个唯一用例）。
        tc.variables["USE_GTEST"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # ── 上游官方测试（层 1，R51）：62 个 CTest 用例在本机原生执行 ──
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["OpenIGTLink"]
        # 上游 Source/CMakeLists.txt 以 PUBLIC 方式链接 m 与 pthread。
        self.cpp_info.system_libs = ["m", "pthread"]
        self.cpp_info.set_property("cmake_file_name", "OpenIGTLink")
        self.cpp_info.set_property("cmake_target_name", "OpenIGTLink::OpenIGTLink")
