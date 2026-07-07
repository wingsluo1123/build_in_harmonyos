#!/usr/bin/env python3
"""Conan recipe — basis_universal v2.1.0 (CMake project).

basis_universal is an LDR/HDR portable GPU supercompressed texture transcoding system.
The CMake build produces basisu_encoder library but doesn't have install targets,
so we manually copy the built files.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BasisuniversalConan(ConanFile):
    name = "basis_universal"
    version = "v2.1.0"
    description = "An LDR/HDR portable GPU supercompressed texture transcoding system"
    license = "MIT"
    homepage = "https://github.com/BinomialLLC/basis_universal"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

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
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # The CMakeLists.txt doesn't have install targets, so manually copy files
        # Copy the built static library
        copy(self, "*.a", self.build_folder, os.path.join(self.package_folder, "lib"))
        # Copy headers
        copy(self, "*.h", os.path.join(self.source_folder, "encoder"),
             os.path.join(self.package_folder, "include", "basis_universal", "encoder"))
        copy(self, "*.h", os.path.join(self.source_folder, "transcoder"),
             os.path.join(self.package_folder, "include", "basis_universal", "transcoder"))
        # Copy any root-level headers
        copy(self, "*.h", self.source_folder, os.path.join(self.package_folder, "include", "basis_universal"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["basisu_encoder"]
