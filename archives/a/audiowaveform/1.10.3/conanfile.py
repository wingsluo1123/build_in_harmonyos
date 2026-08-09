#!/usr/bin/env python3
"""Conan recipe for audiowaveform 1.10.3.

Audio Waveform Image Generator — generates waveform data and renders
waveform images from audio files.

Homepage: https://github.com/bbc/audiowaveform
License: GPL-3.0

Dependencies (libgd, libsndfile, libmad, libid3tag, boost) are built
system-wide and found via CMAKE_PREFIX_PATH. They will be migrated
to Conan requirements() as they become available in the ohpcd registry.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AudiowaveformConan(ConanFile):
    name = "audiowaveform"
    version = "1.10.3"
    description = "Generate waveform images and JSON data from audio files"
    license = "GPL-3.0"
    homepage = "https://github.com/bbc/audiowaveform"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Disable tests (googletest) and enable static build
        tc.variables["ENABLE_TESTS"] = "OFF"
        tc.variables["BUILD_STATIC"] = "ON"
        # Dependencies are installed system-wide during local development.
        # TODO: Once deps are published to ohpcd registry, add requirements()
        # and remove this CMAKE_PREFIX_PATH fallback.
        deps_prefix = os.environ.get("OHPCD_DEPS_PREFIX", "")
        if deps_prefix:
            tc.cache_variables["CMAKE_PREFIX_PATH"] = deps_prefix
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
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
