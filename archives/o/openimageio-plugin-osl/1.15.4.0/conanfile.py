#!/usr/bin/env python3
"""Conan recipe for OSL (Open Shading Language) as OpenImageIO plugin.

OSL is an advanced shading language for VFX rendering, compiled as an
OpenImageIO plugin. Built with CMake, requires OpenImageIO, LLVM, Imath,
pugixml, and zlib.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class OpenimageioPluginOslConan(ConanFile):
    name = "openimageio-plugin-osl"
    version = "1.15.4.0"
    description = "OpenShadingLanguage — advanced shading language for VFX rendering (OIIO plugin)"
    license = "Apache-2.0"
    homepage = "https://github.com/AcademySoftwareFoundation/OpenShadingLanguage"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "build_plugins": [True, False],
    }
    default_options = {
        "shared": True,
        "build_plugins": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openimageio/3.1.13.1")
        self.requires("imath/3.2.2")
        self.requires("openexr/3.1.5")
        self.requires("llvm/20.1.0")
        self.requires("pugixml/1.15-r0")
        self.requires("zlib/1.3.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Build as shared library (OSL produces .so plugins)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        # Disable Python bindings to avoid dependency issues
        tc.variables["USE_PYTHON"] = "OFF"
        # Disable Qt (osltoy not needed)
        tc.variables["USE_QT"] = "OFF"
        # Build OIIO plugin
        tc.variables["OSL_BUILD_PLUGINS"] = "ON" if self.options.build_plugins else "OFF"
        # Disable tests
        tc.variables["OSL_BUILD_TESTS"] = "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        # Disable CUDA/OptiX (not available on OHOS)
        tc.variables["OSL_USE_OPTIX"] = "OFF"
        tc.variables["USE_LLVM_BITCODE"] = "OFF"
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
        # OSL produces multiple libraries
        self.cpp_info.libs = [
            "oslcomp",
            "oslexec",
            "oslquery",
            "oslnoise",
        ]
        # The OIIO plugin is installed to the plugin directory
        self.cpp_info.resdirs = ["share"]
