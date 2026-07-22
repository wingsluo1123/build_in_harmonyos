#!/usr/bin/env python3
"""Conan recipe for SDL3_ttf 3.2.2 on OpenHarmony PC.

SDL3_ttf is the TrueType/OpenType font rendering companion to SDL3.
It depends on SDL3 plus a FreeType2 library (which upstream can
either vendor from `external/freetype/` or pull from a system /
conan-provided FreeType via `find_package(Freetype)`).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Sdl3TtfConan(ConanFile):
    name = "sdl3_ttf"
    version = "3.2.2"
    description = ("SDL3_ttf is a TrueType / OpenType / FreeType font "
                   "rendering library for SDL3. Companion to SDL3_image.")
    license = "Zlib"
    homepage = "https://github.com/libsdl-org/SDL_ttf"
    url = "https://github.com/libsdl-org/SDL_ttf/releases/tag/release-3.2.2"
    topics = ("sdl", "ttf", "font", "freetype", "graphics")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    # CMakeDeps is REQUIRED so SDL3_ttf's upstream CMakeLists.txt can
    # `find_package(SDL3)` and pick up the conan-generated SDL3Config.cmake.
    # CMakeToolchain is added implicitly by cmake_layout().
    generators = "CMakeDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # SDL3_ttf >= 3.2 needs SDL3 >= 3.4.0; require the same revision
        # that this migration produced.
        self.requires("sdl3/3.4.8@ohpcd/stable")
        # SDL3_ttf needs a FreeType2 implementation. We use the conan-
        # provided freetype/2.14.3 (also built in this migration) instead
        # of SDL3_ttf's vendored external/freetype tree because the
        # vendored tree only ships its sources via `download.sh`
        # (git submodule clone) — fragile on CI and not reproducible.
        # SDLTTF_VENDORED=OFF below makes upstream's CMakeLists.txt
        # route through find_package(Freetype REQUIRED) which conan's
        # CMakeDeps satisfies via freetypeConfig.cmake.
        self.requires("freetype/2.14.3@ohpcd/stable")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Static-only (R26-style discipline).
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        # Use conan-provided freetype, not the vendored external/freetype
        # tree (which is an empty git submodule placeholder on a fresh
        # source checkout).
        tc.variables["SDLTTF_VENDORED"] = "OFF"
        # HarfBuzz (OpenType shaping) is OPTIONAL; SDL3_ttf auto-disables
        # it if not found. We don't pull harfbuzz to keep the dep graph
        # minimal — INSTEAD renders Latin/Cyrillic fine without it.
        # plutosvg (SVG color glyphs) similarly opt-in / opt-out; we
        # skip it.
        tc.variables["SDLTTF_HARFBUZZ"] = "OFF"
        tc.variables["SDLTTF_PLUTOSVG"] = "OFF"
        # Output.
        tc.variables["SDLTTF_SHARED"] = "OFF"
        tc.variables["SDLTTF_STATIC"] = "ON"
        # Skip samples / tests — R34 covers these via our test_package.
        tc.variables["SDLTTF_SAMPLES"] = "OFF"
        tc.variables["SDLTTF_TESTS"] = "OFF"
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
        # SDL3_ttf upstream builds either SDL3_ttf::SDL3_ttf-shared or
        # SDL3_ttf::SDL3_ttf-static. We expose just the static library
        # to consumers as `SDL3_ttf`.
        self.cpp_info.libs = ["SDL3_ttf"]
        self.cpp_info.system_libs = ["pthread"]

    def package_id(self):
        # Bionic libc++ ABI is consistent across OHOS profiles.
        del self.info.settings.compiler.libcxx