#!/usr/bin/env python3
"""Conan recipe for vgmstream r2117 — CMake-based audio library + CLI tool.

vgmstream is a library for playing streamed audio from video games.
Build system: CMake (NOT autotools).
Dependencies: ffmpeg, libao, libvorbis, mpg123, speex, libogg (all optional,
  can be disabled for minimal builds).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class VgmstreamConan(ConanFile):
    name = "vgmstream"
    version = "r2117"
    description = "Library for playing streamed audio from video games (vgmstream)"
    license = "MIT"
    homepage = "https://github.com/vgmstream/vgmstream"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "use_ffmpeg": [True, False],
        "use_mpeg": [True, False],
        "use_vorbis": [True, False],
        "use_speex": [True, False],
        "use_celt": [True, False],
        "use_g719": [True, False],
        "use_atrac9": [True, False],
        "build_audacious": [True, False],
        "build_v123": [True, False],
    }
    default_options = {
        "shared": False,
        "use_ffmpeg": False,
        "use_mpeg": False,
        "use_vorbis": False,
        "use_speex": False,
        "use_celt": False,
        "use_g719": False,
        "use_atrac9": False,
        "build_audacious": False,
        "build_v123": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        if self.options.use_ffmpeg:
            self.requires("ffmpeg/8.1.1")
        if self.options.use_mpeg:
            self.requires("mpg123/1.33.5")
        if self.options.use_vorbis:
            self.requires("libvorbis/1.3.7")
            self.requires("libogg/1.3.6")
        if self.options.use_speex:
            self.requires("speex/1.2.1")
            self.requires("libogg/1.3.6")
        if self.options.build_v123:
            self.requires("libao/1.2.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: System-name libraries default to static
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["BUILD_AUDACIOUS"] = self.options.build_audacious
        tc.variables["BUILD_V123"] = self.options.build_v123
        tc.variables["BUILD_CLI"] = "ON"
        tc.variables["USE_FFMPEG"] = self.options.use_ffmpeg
        tc.variables["USE_MPEG"] = self.options.use_mpeg
        tc.variables["USE_VORBIS"] = self.options.use_vorbis
        tc.variables["USE_SPEEX"] = self.options.use_speex
        tc.variables["USE_CELT"] = self.options.use_celt
        tc.variables["USE_G719"] = self.options.use_g719
        tc.variables["USE_ATRAC9"] = self.options.use_atrac9
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

        # vgmstream's CMakeLists.txt has no install rules for the static
        # library (libvgmstream) or headers — only the CLI binary is
        # installed via cmake.install().  We must manually copy them.

        # 1. Copy the static library libvgmstream.a to lib/
        #    The CMake build places it in {build_folder}/src/libvgmstream.a
        #    keep_path=False flattens the directory structure so the .a file
        #    ends up directly in lib/ (not lib/src/)
        copy(self, "*.a",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"),
             keep_path=False)

        # 2. Copy all public headers from src/ to include/
        #    Preserves subdirectory structure (util/, coding/, etc.)
        #    so relative includes like #include "util/vgmstream_limits.h" work.
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"))

        # 3. Copy external header pstdint.h
        copy(self, "pstdint.h",
             src=os.path.join(self.source_folder, "ext_includes"),
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["vgmstream"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]

