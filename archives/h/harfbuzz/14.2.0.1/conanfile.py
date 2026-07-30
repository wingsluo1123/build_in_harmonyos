#!/usr/bin/env python3
"""Conan recipe for harfbuzz 14.2.0 — CMake build system with graphite2 support.

HarfBuzz is a text shaping library for OpenType fonts.
This recipe builds the library using CMake with graphite2 and freetype support.

This recipe enforces R5/R26: static linking by default.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class HarfbuzzConan(ConanFile):
    name = "harfbuzz"
    version = "14.2.0.1"
    description = "HarfBuzz is a text shaping library for OpenType fonts"
    license = "MIT"
    homepage = "https://harfbuzz.github.io/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "with_graphite2": [True, False],
        "with_freetype": [True, False],
    }
    default_options = {
        "shared": False,
        "with_graphite2": True,
        "with_freetype": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R36: dependencies must be published before building downstream
        if self.options.with_graphite2:
            self.requires("graphite2/1.3.14")
        if self.options.with_freetype:
            self.requires("freetype/2.14.3")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R5/R26: build static by default
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        # Enable graphite2 support (HB_HAVE_GRAPHITE2)
        tc.variables["HB_HAVE_GRAPHITE2"] = self.options.with_graphite2
        # Enable freetype support (HB_HAVE_FREETYPE)
        tc.variables["HB_HAVE_FREETYPE"] = self.options.with_freetype
        # Disable features not available on OHOS
        tc.variables["HB_HAVE_GLIB"] = False
        tc.variables["HB_HAVE_ICU"] = False
        tc.variables["HB_HAVE_CAIRO"] = False
        tc.variables["HB_HAVE_GOBJECT"] = False
        tc.variables["HB_BUILD_UTILS"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # CMAKE_POLICY_VERSION_MINIMUM must be passed as cache variable
        # because CMake 4.x checks cmake_minimum_required() before
        # processing toolchain file variables
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()
        # L1: Run upstream official test suite (ctest)
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

        # If CMake install didn't copy libraries, do it manually
        lib_dir = os.path.join(self.package_folder, "lib")
        if not os.path.exists(lib_dir):
            os.makedirs(lib_dir, exist_ok=True)
        for lib_name in ("libharfbuzz.a", "libharfbuzz-subset.a",
                         "libharfbuzz-vector.a", "libharfbuzz-raster.a",
                         "libharfbuzz-gpu.a"):
            build_lib = os.path.join(self.build_folder, lib_name)
            if os.path.exists(build_lib) and not os.path.exists(os.path.join(lib_dir, lib_name)):
                shutil.copy2(build_lib, lib_dir)

    def package_info(self):
        # Headers are installed to include/harfbuzz/, so consumers can
        # use #include <hb.h> directly
        self.cpp_info.includedirs = ["include/harfbuzz"]

        # Components: harfbuzz produces multiple independent libraries
        self.cpp_info.components["harfbuzz"].libs = ["harfbuzz"]
        self.cpp_info.components["harfbuzz"].includedirs = ["include/harfbuzz"]
        self.cpp_info.components["harfbuzz"].set_property("pkg_config_name", "harfbuzz")
        self.cpp_info.components["subset"].libs = ["harfbuzz-subset"]
        self.cpp_info.components["subset"].includedirs = ["include/harfbuzz"]
        self.cpp_info.components["subset"].requires = ["harfbuzz"]
        self.cpp_info.components["subset"].set_property("pkg_config_name", "harfbuzz-subset")
        self.cpp_info.components["vector"].libs = ["harfbuzz-vector"]
        self.cpp_info.components["vector"].includedirs = ["include/harfbuzz"]
        self.cpp_info.components["vector"].requires = ["harfbuzz"]
        self.cpp_info.components["vector"].set_property("pkg_config_name", "harfbuzz-vector")

        # Transitive dependencies: harfbuzz public headers include
        # graphite2 and freetype headers (e.g., hb-graphite2.h includes
        # <graphite2/Font.h>, hb-ft.h includes <ft2build.h>)
        _requires = []
        if self.options.with_graphite2:
            _requires.append("graphite2::graphite2")
        if self.options.with_freetype:
            _requires.append("freetype::freetype")
        self.cpp_info.components["harfbuzz"].requires = _requires
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.components["harfbuzz"].system_libs = ["pthread", "m"]
