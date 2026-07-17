#!/usr/bin/env python3
"""Conan recipe for avro-c 1.12.1.

Apache Avro C library — data serialization system with codec support
(deflate, snappy, lzma). Produces libavro + command-line tools
(avroappend, avrocat, avromod, avropipe).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AvroCConan(ConanFile):
    name = "avro-c"
    version = "1.12.1"
    description = "Apache Avro data serialization system (C implementation)"
    license = "Apache-2.0"
    homepage = "https://avro.apache.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("jansson/2.15.0")
        self.requires("snappy/1.2.2")
        self.requires("xz/5.6.2")
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # snappy is a C++ library; linking to C project needs -lc++
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = (tc.variables.get("CMAKE_EXE_LINKER_FLAGS", "") + " -lc++").strip()
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
        self.cpp_info.libs = ["avro"]
