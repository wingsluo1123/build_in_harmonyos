#!/usr/bin/env python3
"""Conan 2.x recipe — SDL2_ttf 2.24.0

TrueType font library for SDL2. CMake build (autotools fails on HMDFS).
External dependencies: SDL2, FreeType, HarfBuzz, libpng, zlib.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class Sdl2TtfConan(ConanFile):
    name = "sdl2_ttf"
    version = "2.24.0"
    description = "TrueType font library for SDL2 applications"
    license = "zlib"
    homepage = "https://github.com/libsdl-org/SDL_ttf"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("sdl2/2.30.10")
        self.requires("freetype/2.14.3")
        self.requires("harfbuzz/14.2.0")

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        sdl2_dependency = self.dependencies["sdl2"]
        sdl2 = sdl2_dependency.cpp_info
        sdl2_include = os.path.join(
            sdl2_dependency.package_folder, "include", "SDL2"
        )
        if sdl2_include not in sdl2.includedirs:
            sdl2.includedirs.append(sdl2_include)
        sdl2.set_property("cmake_file_name", "SDL2")
        sdl2.set_property(
            "cmake_target_name",
            "SDL2::SDL2"
            if sdl2_dependency.options.shared
            else "SDL2::SDL2-static",
        )

        freetype = self.dependencies["freetype"].cpp_info
        freetype.set_property("cmake_file_name", "Freetype")
        freetype.set_property("cmake_target_name", "Freetype::Freetype")

        CMakeDeps(self).generate()
        if self.settings.os == "OHOS":
            tc = CMakeToolchain(self, generator="Ninja")
        else:
            tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        if self.options.get_safe("fPIC") is not None:
            tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.fPIC)
        tc.variables["SDL2TTF_HARFBUZZ"] = True
        tc.variables["SDL2TTF_FREETYPE"] = True
        tc.variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = True
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
        self.cpp_info.libs = ["SDL2_ttf"]
        self.cpp_info.requires = [
            "sdl2::sdl2",
            "freetype::freetype",
            "harfbuzz::harfbuzz",
        ]
        self.cpp_info.set_property("cmake_file_name", "SDL2_ttf")
        self.cpp_info.set_property("cmake_target_name", "SDL2_ttf::SDL2_ttf")
