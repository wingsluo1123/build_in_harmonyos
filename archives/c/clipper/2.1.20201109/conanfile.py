#!/usr/bin/env python3
"""Conan recipe — clipper 2.1.20201109 (CCP4 crystallographic library, CMake)."""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ClipperConan(ConanFile):
    name = "clipper"
    version = "2.1.20201109"
    description = "CCP4 clipper — object-oriented libraries for crystallographic data and computation"
    license = "GPL-2.0-or-later"
    homepage = "https://ccp4forge.rc-harwell.ac.uk/ccp4/clipper"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libccp4/8.0.0")
        self.requires("mmdb/2.0.22")
        self.requires("fftw/2.1.5")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["CMAKE_CXX_FLAGS"] = "-DFFTW2_PREFIX_S"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # OHOS worker sandboxes reject make's jobserver mkfifo and fork
        # under parallel load (EPERM/EAGAIN) — build serially for reliability.
        cmake.build(build_tool_args=["-j1"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), ignore_case=True)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Clipper")
        self.cpp_info.set_property("pkg_config_name", "clipper")

        self.cpp_info.components["clipper-core"].set_property("cmake_target_name", "Clipper::clipper-core")
        self.cpp_info.components["clipper-core"].libs = ["clipper-core"]
        self.cpp_info.components["clipper-core"].requires = ["fftw::fftw"]

        self.cpp_info.components["clipper-contrib"].set_property("cmake_target_name", "Clipper::clipper-contrib")
        self.cpp_info.components["clipper-contrib"].libs = ["clipper-contrib"]
        self.cpp_info.components["clipper-contrib"].requires = ["clipper-core"]

        self.cpp_info.components["clipper-cns"].set_property("cmake_target_name", "Clipper::clipper-cns")
        self.cpp_info.components["clipper-cns"].libs = ["clipper-cns"]
        self.cpp_info.components["clipper-cns"].requires = ["clipper-core"]

        self.cpp_info.components["clipper-phs"].set_property("cmake_target_name", "Clipper::clipper-phs")
        self.cpp_info.components["clipper-phs"].libs = ["clipper-phs"]
        self.cpp_info.components["clipper-phs"].requires = ["clipper-core"]

        self.cpp_info.components["clipper-mmdb"].set_property("cmake_target_name", "Clipper::clipper-mmdb")
        self.cpp_info.components["clipper-mmdb"].libs = ["clipper-mmdb"]
        self.cpp_info.components["clipper-mmdb"].requires = ["clipper-core", "mmdb::mmdb"]

        self.cpp_info.components["clipper-ccp4"].set_property("cmake_target_name", "Clipper::clipper-ccp4")
        self.cpp_info.components["clipper-ccp4"].libs = ["clipper-ccp4"]
        self.cpp_info.components["clipper-ccp4"].requires = ["clipper-core", "libccp4::libccp4", "mmdb::mmdb"]

        self.cpp_info.components["clipper-minimol"].set_property("cmake_target_name", "Clipper::clipper-minimol")
        self.cpp_info.components["clipper-minimol"].libs = ["clipper-minimol"]
        self.cpp_info.components["clipper-minimol"].requires = ["clipper-core", "clipper-mmdb", "libccp4::libccp4", "mmdb::mmdb"]

        self.cpp_info.components["clipper-cif"].set_property("cmake_target_name", "Clipper::clipper-cif")
        self.cpp_info.components["clipper-cif"].libs = ["clipper-cif"]
        self.cpp_info.components["clipper-cif"].requires = ["clipper-core", "clipper-mmdb", "libccp4::libccp4", "mmdb::mmdb"]
