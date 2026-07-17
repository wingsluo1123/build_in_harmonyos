#!/usr/bin/env python3
"""Conan recipe — curlpp 0.8.1 (CMake)

Uses system curl (pre-installed via cmd-pkgs). The curl installation path
is passed via DEFAULT_PREFIX environment variable or user.curl:prefix conf.
"""

import os

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
        # curl is system-preinstalled; locate via Conan conf or DEFAULT_PREFIX env
        curl_prefix = self.conf.get("user.curl:prefix", default="", check_type=str)
        if not curl_prefix:
            curl_prefix = os.environ.get("DEFAULT_PREFIX", "")
        if curl_prefix:
            tc.variables["CMAKE_PREFIX_PATH"] = curl_prefix
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
