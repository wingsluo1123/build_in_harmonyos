#!/usr/bin/env python3
"""Conan recipe — libmad 0.16.4 (CMake build)."""
import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches

class LibmadConan(ConanFile):
    name = "libmad"
    version = "0.16.4"
    description = "High-quality MPEG audio decoder library"
    license = "GPL-2.0-or-later"
    homepage = "https://www.underbit.com/products/mad/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False], "ASO": [True, False]}
    default_options = {"shared": True, "fPIC": True, "ASO": False}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"libmad supports Linux and OHOS, got {self.settings.os}")
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.cache_variables["ASO"] = "OFF"
        tc.cache_variables["EXAMPLE"] = "OFF"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["mad"]
        self.cpp_info.set_property("cmake_file_name", "mad")
        self.cpp_info.set_property("cmake_target_name", "mad::mad")
        self.cpp_info.set_property("pkg_config_name", "mad")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
