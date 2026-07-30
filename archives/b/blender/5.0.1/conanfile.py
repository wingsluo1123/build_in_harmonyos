#!/usr/bin/env python3
"""Conan recipe template — Blender 5.0.1 for HarmonyOS (OHOS)

Blender is a professional 3D creation suite. This recipe builds Blender
for OHOS aarch64 in headless mode (rendering only, no GUI).

Key adaptation points:
- Headless build: WITH_HEADLESS=ON, disabled GUI subsystems
- OHOS platform: Added to CMake platform detection
- GPU disabled: No CUDA/HIP/OpenCL on OHOS
- Python disabled: Reduces complexity for OHOS port
"""

import os
from pathlib import Path

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class BlenderConan(ConanFile):
    name = "blender"
    version = "5.0.1"
    description = "Professional 3D creation suite - OHOS headless build"
    license = "GPL-3.0-or-later"
    homepage = "https://www.blender.org/"
    url = ""

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "with_cycles": [True, False],
        "with_ffmpeg": [True, False],
        "with_openimageio": [True, False],
    }
    default_options = {
        "shared": False,
        "with_cycles": False,
        "with_ffmpeg": False,
        "with_openimageio": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Core dependencies - all using @ohpcd/stable format
        # zlib is a system library on OHOS, usually available
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)

        # Platform settings
        # Platform settings - use Linux toolchain path which is the closest match
        # for OHOS aarch64 (musl libc is handled by the OHOS sysroot)
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"

        # Headless mode - essential for OHOS server/renderfarm
        tc.variables["WITH_HEADLESS"] = "ON"
        tc.variables["WITH_GHOST_X11"] = "OFF"
        tc.variables["WITH_GHOST_WAYLAND"] = "OFF"
        tc.variables["WITH_GHOST_SDL"] = "OFF"

        # Disable GPU features (no CUDA/HIP/OpenCL on OHOS)
        tc.variables["WITH_CYCLES"] = "ON" if self.options.with_cycles else "OFF"
        tc.variables["WITH_CYCLES_CUDA_BINARIES"] = "OFF"
        tc.variables["WITH_CYCLES_HIP_BINARIES"] = "OFF"
        tc.variables["WITH_CYCLES_EMBREE"] = "OFF"
        tc.variables["WITH_CYCLES_OSL"] = "OFF"
        tc.variables["WITH_CYCLES_OPTIX"] = "OFF"

        # Disable Python (simplifies OHOS adaptation)
        tc.variables["WITH_PYTHON"] = "OFF"

        # Disable unnecessary features for headless
        tc.variables["WITH_BLENDER_THUMBNAILER"] = "OFF"
        tc.variables["WITH_FFTW3"] = "OFF"
        tc.variables["WITH_MOD_FLUID"] = "OFF"
        tc.variables["WITH_MOD_OCEANSIM"] = "OFF"
        tc.variables["WITH_BULLET"] = "OFF"
        tc.variables["WITH_OPENVDB"] = "OFF"
        tc.variables["WITH_ALEMBIC"] = "OFF"
        tc.variables["WITH_USD"] = "OFF"

        # Codecs - optional
        tc.variables["WITH_CODEC_FFMPEG"] = "ON" if self.options.with_ffmpeg else "OFF"
        tc.variables["WITH_CODEC_SNDFILE"] = "OFF"

        # Image formats - essential
        tc.variables["WITH_IMAGE_OPENEXR"] = "ON"
        tc.variables["WITH_IMAGE_TIFF"] = "ON"
        tc.variables["WITH_IMAGE_PNG"] = "ON"
        tc.variables["WITH_IMAGE_JPEG"] = "ON"

        # OpenImageIO - optional
        tc.variables["WITH_OPENIMAGEIO"] = "ON" if self.options.with_openimageio else "OFF"

        # Internationalization
        tc.variables["WITH_INTERNATIONAL"] = "OFF"

        # Disable tests in build (we run them separately)
        tc.variables["WITH_TESTS"] = "OFF"

        # Build settings
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["CMAKE_BUILD_TYPE"] = str(self.settings.build_type) if self.settings.build_type else "Release"

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
        # Blender is primarily an application, no public linkable libraries
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = ["c"]  # musl libc on OHOS
