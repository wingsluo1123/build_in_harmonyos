#!/usr/bin/env python3
import os
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BackwardCppConan(ConanFile):
    name = "backward-cpp"
    version = "1.6"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    # library 类型必须声明 shared 选项（conan 2 校验——cattle/sherlock.lv2 先例）
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    # 导出 patches/（apply_conandata_patches 需要——multitail 教训）
    exports_sources = "patches/*"
    # 无外部依赖（backward-cpp 为单头文件 backward.hpp + backward.cpp 实现——
    # C++ 堆栈回溯库）

    def layout(self):
        cmake_layout(self)

    def source(self):
        # 显式应用 0001-dl_info-compat.patch（multitail 教训：必须显式调用
        # apply_conandata_patches——否则补丁不会被应用）
        from conan.tools.files import apply_conandata_patches
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # 静态链接偏好（BUILD_SHARED_LIBS=OFF——shared=False 默认）
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        # 上游测试（test/ 套件）在本地/CI 验证（构建时关闭测试目标）
        tc.variables["BACKWARD_ENABLE_TEST"] = "OFF"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 单头文件 backward.hpp 是核心 API（确保打包到 include/）
        self.copy("backward.hpp", dst="include", src=".")

    def package_info(self):
        self.cpp_info.libs = ["backward"]
        self.cpp_info.includedirs = ["include"]
