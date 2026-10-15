#!/usr/bin/env python3
"""Conan recipe — cpp-member-accessor 1.0.0 (CMake header-only library).

Header-only C++17 library enabling access to private data members via
explicit class template instantiation (legal per the standard).
No binary is compiled; only headers and the CMake package config are installed.
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
import os


class CppMemberAccessorConan(ConanFile):
    name = "cpp-member-accessor"
    version = "1.0.0"
    description = "Header-only C++ library for accessing private data members"
    license = "MIT"
    homepage = "https://github.com/hliberacki/cpp-member-accessor"
    url = ""  # CI fills this
    topics = ("c++", "templates", "access-private-members", "header-only")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # R32: 平台判断必须 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS", "FreeBSD", "Macos", "Windows"):
            raise ConanInvalidConfiguration(
                "cpp-member-accessor 只支持 Linux/OHOS/FreeBSD/Macos/Windows，当前: {}".format(self.settings.os))

    def layout(self):
        cmake_layout(self)

    def package_id(self):
        # header-only 库，所有 settings 组合产出相同的包内容
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake does not recognize OHOS as a target platform
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.variables["CMAKE_CXX_STANDARD"] = 17
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = True
        tc.variables["EXAMPLES"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if not cross_building(self):
            cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 兜底：确保头文件进入包内（上游 install(DIRECTORY include/) 已覆盖）
        copy(self, "*.hpp*", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"), keep_path=True)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "accessor")
        self.cpp_info.set_property("cmake_target_name", "accessor")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
