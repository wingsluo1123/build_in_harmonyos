#!/usr/bin/env python3
"""Conan 2.x recipe — SDL2_ttf 2.24.0

TrueType font library for SDL2. CMake build (autotools fails on HMDFS).
External dependencies: SDL2, FreeType, HarfBuzz, libpng, zlib.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Sdl2TtfConan(ConanFile):
    name = "sdl2_ttf"
    version = "2.24.0"
    description = "TrueType font library for SDL2 applications"
    license = "zlib"
    homepage = "https://github.com/libsdl-org/SDL_ttf"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("SDL2/2.30.0@ohpcd/stable")
        self.requires("freetype/26.6.20@ohpcd/stable")
        self.requires("harfbuzz/14.2.0@ohpcd/stable")
        self.requires("libpng/16.39.0@ohpcd/stable")
        self.requires("zlib/1.3.1@ohpcd/stable")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["SDL2TTF_HARFBUZZ"] = "ON"
        tc.variables["SDL2TTF_FREETYPE"] = "ON"
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
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
