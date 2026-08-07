#!/usr/bin/env python3
"""Conan recipe for OpenShadingLanguage (OSL) — OIIO plugin.

OSL is the Open Shading Language, an advanced shading language for VFX
rendering. This package builds OSL as a set of libraries and an OpenImageIO
plugin.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class OpenimageioPluginOslConan(ConanFile):
    name = "openimageio-plugin-osl"
    version = "1.15.4.0"
    description = "OpenShadingLanguage — advanced shading language for VFX rendering (OIIO plugin)"
    license = "Apache-2.0"
    homepage = "https://github.com/AcademySoftwareFoundation/OpenShadingLanguage"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openimageio/3.1.13.1")
        self.requires("imath/3.2.2")
        self.requires("llvm/20.1.0")
        self.requires("pugixml/1.15-r0")
        self.requires("zlib/1.3.1.1")
        self.requires("robin-map/1.4.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Disable optional features not needed on OHOS
        tc.variables["USE_PYTHON"] = "OFF"
        tc.variables["USE_QT"] = "OFF"
        tc.variables["OSL_USE_OPTIX"] = "OFF"
        tc.variables["OSL_BUILD_TESTS"] = "OFF"
        tc.variables["OSL_BUILD_SHADERS"] = "OFF"
        tc.variables["INSTALL_DOCS"] = "OFF"
        tc.variables["USE_LLVM_BITCODE"] = "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        # Let Conan manage dependencies via CMakeDeps
        tc.variables["BUILD_MISSING_DEPS"] = "OFF"
        tc.variables["BUILD_MISSING_ROBINMAP"] = "OFF"
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
        self.cpp_info.libs = ["oslcomp", "oslexec", "oslquery", "oslnoise"]
        self.cpp_info.set_property("cmake_file_name", "OSL")
        self.cpp_info.set_property("cmake_target_name", "OSL::OSL")
