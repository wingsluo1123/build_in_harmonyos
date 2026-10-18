#!/usr/bin/env python3
"""Conan recipe for ECOS 2.0.10 (CMake)."""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
import os


class EcosConan(ConanFile):
    name = "ecos"
    version = "2.0.10"
    description = "Embedded conic solver with exponential cones and mixed integer support"
    license = "GPL-3.0-or-later", "LGPL-2.1-or-later"
    homepage = "https://github.com/embotech/ecos"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False], "use_long": [True, False]}
    default_options = {"shared": False, "fPIC": True, "use_long": True}
    exports_sources = "licenses/*"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            filename="ecos-2.0.10.tar.gz", strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["USE_LONG"] = bool(self.options.use_long)
        tc.variables["ECOS_BUILD_TESTS"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.ctest(cli_args=["--output-on-failure"])

    def package(self):
        CMake(self).install()
        for directory in ["", "external/amd", "external/ldl", "external/SuiteSparse_config"]:
            copy(self, "*LICENSE*", os.path.join(self.source_folder, directory),
                 os.path.join(self.package_folder, "licenses", directory))
        copy(self, "COPYING*", self.source_folder, os.path.join(self.package_folder, "licenses"))
        for directory in ["external/amd", "external/ldl"]:
            copy(self, "README.txt", os.path.join(self.source_folder, directory),
                 os.path.join(self.package_folder, "licenses", directory))
        copy(self, "SuiteSparse_config.h", os.path.join(self.source_folder, "external/SuiteSparse_config"),
             os.path.join(self.package_folder, "licenses", "external/SuiteSparse_config"))
        copy(self, "*", os.path.join(self.source_folder, "licenses"),
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["ecos"]
        self.cpp_info.includedirs = ["include/ecos"]
        self.cpp_info.set_property("cmake_file_name", "ecos")
        self.cpp_info.set_property("cmake_target_name", "ecos::ecos")
        self.cpp_info.defines = ["CTRLC=1"]
        if self.options.use_long:
            self.cpp_info.defines.extend(["DLONG", "LDL_LONG"])
        if self.settings.os != "Windows":
            self.cpp_info.system_libs = ["m"]
