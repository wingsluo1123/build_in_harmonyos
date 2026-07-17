#!/usr/bin/env python3
"""Conan recipe for abseil-cpp 20260107.1 — CMake build."""
import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AbseilCppConan(ConanFile):
    name = "abseil-cpp"
    version = "20260107.1"
    description = "Google 的高性能 C++ 基础库集合，提供字符串处理、容器、并发、时间等核心组件"
    license = "Apache-2.0"
    homepage = "https://abseil.io"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

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
        tc.variables["BUILD_TESTING"] = False
        tc.variables["ABSL_PROPAGATE_CXX_STD"] = True
        tc.variables["ABSL_ENABLE_INSTALL"] = True
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
        self.cpp_info.set_property("cmake_file_name", "absl")
        # Collect all abseil static libraries
        lib_dir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(lib_dir):
            self.cpp_info.libs = [
                f[3:-2] for f in os.listdir(lib_dir)
                if f.startswith("lib") and f.endswith(".a")
            ]
        self.cpp_info.system_libs.append("pthread")
