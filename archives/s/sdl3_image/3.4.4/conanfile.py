#!/usr/bin/env python3
"""Conan recipe for SDL3_image 3.4.4 on OpenHarmony PC.

SDL3_image is the image-loading companion to SDL3. It builds as a static
archive and depends only on SDL3 (via conan requires) plus the vendored
third-party libraries (zlib, libpng, libjpeg-turbo via stb_image) that
ship in SDL3_image's `external/` directory.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Sdl3ImageConan(ConanFile):
    name = "sdl3_image"
    version = "3.4.4"
    description = ("SDL3_image is an image loading library for SDL3 that "
                   "supports BMP, GIF, JPG, LBM, PCX, PNG, PNM, QOI, TGA, "
                   "XCF, XPM, XV, and (optionally) WEBP, AVIF, JXL, TIF, "
                   "SVG via stb_image and other backends.")
    license = "Zlib"
    homepage = "https://github.com/libsdl-org/SDL_image"
    url = "https://github.com/libsdl-org/SDL_image/releases/tag/release-3.4.4"
    topics = ("sdl", "image", "graphics", "multimedia")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    # CMakeDeps is REQUIRED here — without it conan doesn't generate the
    # `sdl3-config.cmake` shim that the upstream CMakeLists.txt's
    # find_package(SDL3) call relies on. CMakeToolchain is added
    # implicitly by `cmake_layout()`.
    generators = "CMakeDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # SDL3_image needs SDL3 >= 3.4.0. We require the @ohpcd/stable
        # revision published by this same migration.
        self.requires("sdl3/3.4.8@ohpcd/stable")
        # SDL3_image's PNG/JPG support transitively needs zlib. We require
        # the conan-provided zlib so the upstream CMakeLists.txt's
        # find_package(ZLIB) call resolves via CMakeDeps instead of
        # trying to build SDL3_image/external/zlib (which has no
        # CMakeLists.txt until the user runs external/download.sh).
        # Pin to @ohpcd/stable explicitly so we don't accidentally pull
        # the conan-center zlib/1.3.1 (different recipe revision that
        # requires patches not in our local cache).
        self.requires("zlib/1.3.1@ohpcd/stable")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Static-only (R26-style discipline).
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        # Use the vendored third-party libraries (zlib, libpng, etc.)
        # is OFF — we route zlib through conan's zlib/1.3.1 package via
        # find_package(ZLIB) instead. SDL3_image's external/zlib/ has no
        # CMakeLists.txt until the user runs external/download.sh, which
        # we'd rather avoid on OHOS. libpng/libjpeg-turbo etc. are still
        # built from SDL3_image's external/ tree because we set
        # SDLIMAGE_VENDORED=OFF only for zlib-equivalents — SDL3_image
        # falls back to stb_image for JPEG (SDLIMAGE_BACKEND_STB=ON)
        # which has no third-party dep.
        tc.variables["SDLIMAGE_VENDORED"] = "OFF"
        # ─── Format backends ────────────────────────────────────────────────
        # Always-on formats (compiled in regardless of platform):
        tc.variables["SDLIMAGE_BMP"] = "ON"
        tc.variables["SDLIMAGE_GIF"] = "ON"
        tc.variables["SDLIMAGE_JPG"] = "ON"
        tc.variables["SDLIMAGE_LBM"] = "ON"
        tc.variables["SDLIMAGE_PCX"] = "ON"
        tc.variables["SDLIMAGE_PNG"] = "ON"
        tc.variables["SDLIMAGE_PNM"] = "ON"
        tc.variables["SDLIMAGE_QOI"] = "ON"
        tc.variables["SDLIMAGE_TGA"] = "ON"
        tc.variables["SDLIMAGE_XCF"] = "ON"
        tc.variables["SDLIMAGE_XPM"] = "ON"
        tc.variables["SDLIMAGE_XV"] = "ON"
        # Heavy formats — disable to keep build time short and avoid
        # pulling in additional vendored dependencies.
        tc.variables["SDLIMAGE_WEBP"] = "OFF"
        tc.variables["SDLIMAGE_AVIF"] = "OFF"
        tc.variables["SDLIMAGE_JXL"] = "OFF"
        tc.variables["SDLIMAGE_TIF"] = "OFF"
        tc.variables["SDLIMAGE_SVG"] = "OFF"
        # Use stb_image for JPEG (no need for libjpeg-turbo).
        tc.variables["SDLIMAGE_BACKEND_STB"] = "ON"
        # ANI: needs Windows resource APIs; skip.
        tc.variables["SDLIMAGE_ANI"] = "OFF"
        # Skip samples and tests — R34 is covered by our test_package.
        tc.variables["SDLIMAGE_SAMPLES"] = "OFF"
        tc.variables["SDLIMAGE_TESTS"] = "OFF"
        # Don't fail on missing optional deps.
        tc.variables["SDLIMAGE_STRICT"] = "OFF"
        # Output.
        tc.variables["SDLIMAGE_SHARED"] = "OFF"
        tc.variables["SDLIMAGE_STATIC"] = "ON"
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
        # Upstream CMake target name: SDL3_image::SDL3_image-static
        # when built statically. We expose the consumer-facing alias
        # `SDL3_image` here.
        self.cpp_info.libs = ["SDL3_image"]
        self.cpp_info.system_libs = ["pthread"]

    def package_id(self):
        # Bionic libc++ ABI is consistent across OHOS profiles.
        del self.info.settings.compiler.libcxx