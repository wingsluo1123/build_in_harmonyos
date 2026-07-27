#!/usr/bin/env python3
"""Conan recipe for openjpeg2 2.5.4, the OpenJPEG libopenjp2 codec library."""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import collect_libs, get


class OpenJpeg2Conan(ConanFile):
    name = "openjpeg2"
    version = "2.5.4"
    description = "Open-source JPEG 2000 codec library"
    license = "BSD-2-Clause"
    homepage = "https://github.com/uclouvain/openjpeg"
    url = "https://github.com/uclouvain/openjpeg"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "thread": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "thread": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)

        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_STATIC_LIBS"] = "OFF" if self.options.shared else "ON"
        tc.variables["BUILD_CODEC"] = "OFF"
        tc.variables["BUILD_DOC"] = "OFF"
        tc.variables["BUILD_JAVA"] = "OFF"
        tc.variables["BUILD_JPIP"] = "OFF"
        tc.variables["BUILD_LUTS_GENERATOR"] = "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["BUILD_THIRDPARTY"] = "OFF"
        tc.variables["BUILD_UNIT_TESTS"] = "OFF"
        tc.variables["BUILD_VIEWER"] = "OFF"
        tc.variables["OPJ_USE_THREAD"] = "ON" if self.options.thread else "OFF"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        libs = collect_libs(self)
        self.cpp_info.libs = libs or ["openjp2"]
        self.cpp_info.includedirs = ["include/openjpeg-2.5"]
        self.cpp_info.set_property("cmake_file_name", "openjpeg2")
        self.cpp_info.set_property("cmake_target_name", "openjpeg2::openjpeg2")
        self.cpp_info.set_property("pkg_config_name", "libopenjp2")
        if not self.options.shared:
            self.cpp_info.defines.append("OPJ_STATIC")
