#!/usr/bin/env python3
"""Conan recipe for avro-c (Apache Avro C library).

Apache Avro data serialization system C implementation with codec support
(deflate, snappy, lzma).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AvroCConan(ConanFile):
    name = "avro-c"
    version = "1.12.0"
    description = "Apache Avro data serialization system C implementation"
    license = "Apache-2.0"
    homepage = "https://avro.apache.org"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {
        "shared": False,
        "zlib/*:fPIC": True,
        "jansson/*:fPIC": True,
        "snappy/*:fPIC": True,
        "xz/*:fPIC": True,
    }

    generators = "CMakeDeps", "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("jansson/2.15.1")
        self.requires("zlib/1.3.1")
        self.requires("snappy/1.1.10")
        self.requires("xz/5.6.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # CMake 4.x compatibility
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # snappy is a C++ library; linking from C requires -lc++
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-lc++"
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
        self.cpp_info.set_property("cmake_file_name", "avro-c")
        self.cpp_info.set_property("cmake_target_name", "avro-c::avro")
        self.cpp_info.set_property("pkg_config_name", "avro-c")
        self.cpp_info.libs = ["avro"]
        self.cpp_info.requires = ["jansson::jansson", "zlib::zlib", "snappy::snappy", "xz::liblzma"]
