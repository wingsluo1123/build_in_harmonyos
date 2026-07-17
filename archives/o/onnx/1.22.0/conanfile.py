#!/usr/bin/env python3
"""Conan recipe for onnx 1.22.0 — CMake build."""
import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class OnnxConan(ConanFile):
    name = "onnx"
    version = "1.22.0"
    description = "Open standard for machine learning interoperability"
    license = "Apache-2.0"
    homepage = "https://onnx.ai"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("protobuf/34.1", transitive_headers=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["ONNX_BUILD_CUSTOM_PROTOBUF"] = False
        tc.variables["ONNX_USE_PROTOBUF_SHARED_LIBS"] = False
        tc.variables["ONNX_USE_LITE_PROTO"] = False
        tc.variables["ONNX_BUILD_TESTS"] = False
        tc.variables["ONNX_BUILD_BENCHMARKS"] = False
        tc.variables["ONNX_ML"] = True
        tc.variables["ONNX_VERIFY_PROTOBUF"] = True
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
        self.cpp_info.set_property("cmake_file_name", "ONNX")
        self.cpp_info.set_property("cmake_target_name", "ONNX::onnx")
        lib_dir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(lib_dir):
            self.cpp_info.libs = [
                f[3:-2] for f in os.listdir(lib_dir)
                if f.startswith("lib") and f.endswith(".a")
            ]
        self.cpp_info.requires.append("protobuf::protobuf")
        self.cpp_info.defines.append("ONNX_ML=1")
