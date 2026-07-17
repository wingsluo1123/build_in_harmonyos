#!/usr/bin/env python3
"""Conan recipe — sdl2_ttf 2.24.0 (CMake).

SDL2_ttf is a sample library for using TrueType fonts in SDL2 applications.
Note: SDL2 and harfbuzz dependencies not yet in registry — CI will use --build=missing.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Sdl2TtfConan(ConanFile):
    name = "sdl2_ttf"
    version = "2.24.0"
    description = "Library for using TrueType fonts in SDL2 applications"
    license = "Zlib"
    homepage = "https://github.com/libsdl-org/SDL_ttf"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("SDL2/2.30.0")
        self.requires("freetype/2.14.3")
        self.requires("libpng/1.6.58")
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["SDL2TTF_HARFBUZZ"] = "ON"
        tc.variables["SDL2TTF_FREETYPE"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(cli_args=["-DCMAKE_POLICY_VERSION_MINIMUM=3.5"])
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["SDL2_ttf"]
