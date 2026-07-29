#!/usr/bin/env python3
"""Conan recipe for GEOS 3.12.1 using CMake."""

import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd, stdcpp_library
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class GeosConan(ConanFile):
    name = "geos"
    version = "3.12.1"
    description = "Geometry Engine Open Source for two-dimensional vector geometry operations"
    license = "LGPL-2.1-or-later"
    homepage = "https://libgeos.org/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("geospatial", "geometry", "ogc", "topology")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        check_min_cppstd(self, 14)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["BUILD_TESTING"] = True
        tc.variables["GEOS_BUILD_DEVELOPER"] = False
        tc.variables["BUILD_BENCHMARKS"] = False
        tc.variables["BUILD_GEOSOP"] = True
        tc.variables["BUILD_ASTYLE"] = False
        tc.variables["BUILD_WEBSITE"] = False
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.test()

    def package(self):
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "GEOS")
        self.cpp_info.set_property("cmake_target_name", "GEOS::geos_c")
        self.cpp_info.set_property("pkg_config_name", "geos")

        flags = self.cpp_info.components["geos_cxx_flags"]
        flags.set_property("cmake_target_name", "GEOS::geos_cxx_flags")
        flags.defines = ["USE_UNSTABLE_GEOS_CPP_API"]

        geos = self.cpp_info.components["geos"]
        geos.set_property("cmake_target_name", "GEOS::geos")
        geos.libs = ["geos"]
        geos.requires = ["geos_cxx_flags"]
        if self.settings.os in ("Linux", "OHOS", "FreeBSD"):
            geos.system_libs.append("m")
        if not self.options.shared:
            libcxx = stdcpp_library(self)
            if libcxx:
                geos.system_libs.append(libcxx)

        geos_c = self.cpp_info.components["geos_c"]
        geos_c.set_property("cmake_target_name", "GEOS::geos_c")
        geos_c.libs = ["geos_c"]
        geos_c.requires = ["geos"]

        self.buildenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
