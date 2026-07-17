#!/usr/bin/env python3
"""Conan recipe for protobuf 34.1 — CMake build."""
import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ProtobufConan(ConanFile):
    name = "protobuf"
    version = "34.1"
    description = "Google's data serialization format library and compiler"
    license = "BSD-3-Clause"
    homepage = "https://github.com/protocolbuffers/protobuf"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("abseil-cpp/20260107.1", transitive_headers=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["protobuf_BUILD_TESTS"] = False
        tc.variables["protobuf_BUILD_CONFORMANCE"] = False
        tc.variables["protobuf_BUILD_EXAMPLES"] = False
        tc.variables["protobuf_BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["protobuf_FORCE_FETCH_DEPENDENCIES"] = False
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
        self.cpp_info.set_property("cmake_file_name", "protobuf")
        self.cpp_info.set_property("cmake_target_name", "protobuf::protobuf")
        self.cpp_info.requires.append("abseil-cpp::abseil-cpp")
        # Collect all protobuf static libraries
        lib_dir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(lib_dir):
            self.cpp_info.libs = [
                f[3:-2] for f in os.listdir(lib_dir)
                if f.startswith("lib") and f.endswith(".a")
            ]
        self.cpp_info.system_libs.append("pthread")
