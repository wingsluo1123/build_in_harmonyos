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
    version = "14.2.0"
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
        self.requires("graphite2/1.3.14")
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
        # CMake 4.x compatibility
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(variables={
            "CMAKE_POLICY_VERSION_MINIMUM": "3.5",
        })
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

        # If CMake install didn't copy the library, do it manually
        lib_dir = os.path.join(self.package_folder, "lib")
        if not os.path.exists(lib_dir):
            os.makedirs(lib_dir, exist_ok=True)
        build_lib = os.path.join(self.build_folder, "libharfbuzz.a")
        if os.path.exists(build_lib) and not os.path.exists(os.path.join(lib_dir, "libharfbuzz.a")):
            shutil.copy2(build_lib, lib_dir)

    def package_info(self):
        # Headers are installed to include/harfbuzz/, so consumers can
        # use #include <hb.h> directly
        self.cpp_info.includedirs = ["include/harfbuzz"]
        self.cpp_info.libs = ["harfbuzz"]
        # Transitive dependencies: harfbuzz public headers include
        # graphite2 and freetype headers (e.g., hb-graphite2.h includes
        # <graphite2/Font.h>, hb-ft.h includes <ft2build.h>)
        self.cpp_info.requires = ["graphite2::graphite2", "freetype::freetype"]
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
