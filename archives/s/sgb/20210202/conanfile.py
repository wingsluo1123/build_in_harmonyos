#!/usr/bin/env python3
"""SGB 20210202 (CMake): independent packaging wrapper, not Stanford GraphBase.

The upstream CWEB masters remain byte-identical. Use their own PROTOTYPES
change files to generate C and headers suitable for modern C compilers.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (apply_conandata_patches, copy,
                              export_conandata_patches, get)


class SgbConan(ConanFile):
    name = "sgb"
    version = "20210202"
    package_type = "static-library"
    description = "Stanford GraphBase combinatorial graph generators and algorithms"
    license = "LicenseRef-Stanford-GraphBase"
    homepage = "https://www-cs-faculty.stanford.edu/~knuth/sgb.html"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "sgb-CMakeLists.txt", "sgb-sample-check.cmake", "sgb-package-config.cmake"

    def export_sources(self):
        # Standard framework hook; this recipe declares no source patches.
        export_conandata_patches(self)

    def build_requirements(self):
        self.tool_requires("cweb/4.12.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        wrapper = os.path.join(self.build_folder, "wrapper")
        os.makedirs(wrapper, exist_ok=True)
        copy(self, "sgb-CMakeLists.txt", self.source_folder, wrapper)
        os.rename(os.path.join(wrapper, "sgb-CMakeLists.txt"),
                  os.path.join(wrapper, "CMakeLists.txt"))
        copy(self, "sgb-sample-check.cmake", self.source_folder, wrapper)
        copy(self, "sgb-package-config.cmake", self.source_folder, wrapper)
        cweb = self.dependencies.build["cweb"]
        tool = os.path.join(cweb.package_folder, "bin", "ctangle")
        tc = CMakeToolchain(self, generator="Ninja")
        tc.cache_variables["SGB_SOURCE_DIR"] = self.source_folder
        tc.cache_variables["SGB_CTANGLE"] = tool
        tc.cache_variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join(self.build_folder, "wrapper"))
        cmake.build(build_tool_args=["-j1"])
        self.run("ctest --output-on-failure --parallel 1", cwd=self.build_folder)

    def package(self):
        CMake(self).install()
        copy(self, "README", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "boilerplate.w", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "README.PROTOTYPES", os.path.join(self.source_folder, "PROTOTYPES"),
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["gb"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.bindirs = []
        self.cpp_info.builddirs = ["lib/cmake/sgb"]
        # Ship an explicit relocatable config. It does not depend on native
        # CMake's globbing of Conan-generated per-configuration fragments.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.set_property("cmake_file_name", "sgb")
        self.cpp_info.set_property("cmake_target_name", "sgb::sgb")
