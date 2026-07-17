#!/usr/bin/env python3
"""Conan recipe — curlpp 0.8.1 (CMake)

Uses system curl (pre-installed). CMake's FindCURL module locates it
automatically via CMAKE_PREFIX_PATH env var and standard system paths.
"""

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class CurlppConan(ConanFile):
    name = "curlpp"
    version = "0.8.1"
    description = "C++ wrapper for libcurl providing object-oriented HTTP request interface"
    license = "MIT"
    homepage = "https://github.com/jpbarrette/curlpp"
    url = "https://github.com/jpbarrette/curlpp"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
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
        self.cpp_info.libs = ["curlpp"]
        self.cpp_info.set_property("cmake_file_name", "curlpp")
        self.cpp_info.set_property("cmake_target_name", "curlpp::curlpp")
        self.cpp_info.set_property("pkg_config_name", "curlpp")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["curl"]
