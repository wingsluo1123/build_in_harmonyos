import os

from conan import ConanFile
from conan.tools.files import get, copy, save, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class B3SumConan(ConanFile):
    name = "b3sum"
    version = "1.8.4"
    description = "BLAKE3 hash function C reference implementation - library and b3sum tool"
    license = "Apache-2.0"
    homepage = "https://github.com/BLAKE3-team/BLAKE3"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Create a root CMakeLists.txt that includes the c/ subdirectory
        # where the actual BLAKE3 CMake project resides
        save(self, "CMakeLists.txt",
             'cmake_minimum_required(VERSION 3.15)\n'
             'project(b3sum C)\n'
             'add_subdirectory(c)\n')

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: Build static library to avoid polluting system lib paths
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        # Use NEON SIMD for aarch64 (OHOS)
        tc.variables["BLAKE3_SIMD_TYPE"] = "neon-intrinsics"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # Manually copy build artifacts instead of cmake.install()
        # (cmake.install() fails due to missing libblake3.pc pkg-config file)
        copy(self, "blake3.h", os.path.join(self.source_folder, "c"),
             os.path.join(self.package_folder, "include"))
        copy(self, "*.a", os.path.join(self.build_folder, "c"),
             os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["blake3"]
        # CMake package name is blake3, not b3sum
        self.cpp_info.set_property("cmake_file_name", "blake3")
        self.cpp_info.set_property("cmake_target_name", "blake3::blake3")
