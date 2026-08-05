#!/usr/bin/env python3
"""Conan recipe — basisu (v2_1_0r)

Basis Universal GPU texture codec command-line compression tool.
Builds the basisu CLI tool and static encoding/transcoding libraries.

Homepage: https://github.com/BinomialLLC/basis_universal
License: Apache-2.0
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class BasisuConan(ConanFile):
    name = "basisu"
    version = "v2_1_0r"
    package_type = "application"
    description = "Basis Universal GPU texture codec command-line compression tool"
    license = "Apache-2.0"
    homepage = "https://github.com/BinomialLLC/basis_universal"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"

    # R32: settings.os must be Linux or OHOS
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

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
        # Feature detection: HAS_QSORT_R indicates qsort_r with GNU signature is available
        # OHOS musl libc does not provide GNU-sig qsort_r; skip _GNU_SOURCE to use C90 fallback
        if str(self.settings.os) != "OHOS":
            tc.variables["CMAKE_C_FLAGS"] = "-DHAS_QSORT_R"
            tc.variables["CMAKE_CXX_FLAGS"] = "-DHAS_QSORT_R"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # Install basisu CLI binary
        bin_dir = os.path.join(self.source_folder, "bin")
        if os.path.isdir(bin_dir):
            copy(self, "basisu", bin_dir, os.path.join(self.package_folder, "bin"))

        # Install the sole static library: libbasisu_encoder.a
        lib_dir = self.build_folder
        if os.path.isdir(lib_dir):
            copy(self, "libbasisu_encoder.a", lib_dir,
                 os.path.join(self.package_folder, "lib"))

        # Install upstream LDR test fixtures for `basisu -test` suite
        test_files_dir = os.path.join(self.source_folder, "test_files")
        if os.path.isdir(test_files_dir):
            ldr_inputs = [
                "black_1x1.png", "white_1x1.png", "wikipedia.png", "alpha0.png",
            ] + ["kodim{:02d}.png".format(i) for i in range(1, 25)]
            for fname in ldr_inputs:
                src = os.path.join(test_files_dir, fname)
                if os.path.isfile(src):
                    copy(self, fname, test_files_dir,
                         os.path.join(self.package_folder, "res", "test_files"))

        # Install all headers from transcoder/ directory
        trans_dir = os.path.join(self.source_folder, "transcoder")
        if os.path.isdir(trans_dir):
            copy(self, "*.h", trans_dir, os.path.join(self.package_folder, "include", "basis_universal"))

    def package_info(self):
        self.cpp_info.libs = ["basisu_encoder"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = ["m", "pthread"]
        self.cpp_info.set_property("cmake_target_name", "basisu::basisu")
