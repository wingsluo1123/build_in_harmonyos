#!/usr/bin/env python3
"""Conan recipe for SDL3_mixer 3.2.4 on OpenHarmony PC.

SDL3_mixer is the audio-mixing companion to SDL3. It bundles its own
built-in decoders for AIFF / WAVE / VOC / AU, and supports a long
list of optional third-party decoders (FLAC, Vorbis, Opus, GME,
libxmp, mpg123, FluidSynth, WavPack) via either system packages or
upstream's vendored `external/` tree.

We intentionally ship only the built-in decoder set — every heavy
optional backend (FLAC, Vorbis, Opus, GME, mod, MP3, wavpack, FluidSynth)
is disabled, because none of them has a Conan recipe in this migration
and vendoring requires `external/download.sh` (fragile git submodule
clone).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Sdl3MixerConan(ConanFile):
    name = "sdl3_mixer"
    version = "3.2.4"
    description = ("SDL3_mixer is a sample multi-channel audio mixer "
                   "library for SDL3. Built-in support for AIFF, WAVE, "
                   "VOC, AU; optional support for FLAC, Vorbis, Opus, "
                   "GME, MOD (libxmp), MP3 (mpg123), WavPack, FluidSynth.")
    license = "Zlib"
    homepage = "https://github.com/libsdl-org/SDL_mixer"
    url = "https://github.com/libsdl-org/SDL_mixer/releases/tag/release-3.2.4"
    topics = ("sdl", "audio", "mixer", "multimedia")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    # CMakeDeps is REQUIRED so SDL3_mixer's upstream CMakeLists.txt can
    # `find_package(SDL3)` and pick up the conan-generated SDL3Config.cmake.
    generators = "CMakeDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # SDL3_mixer >= 3.2 needs SDL3 >= 3.4.0; require the same revision
        # that this migration produced.
        self.requires("sdl3/3.4.8@ohpcd/stable")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Static-only (R26-style discipline).
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        # ─── Backend selection ──────────────────────────────────────────────
        # Built-in decoders (no third-party deps). These are pure SDL3_mixer
        # code that ships in src/codec/; we keep them ON.
        tc.variables["SDLMIXER_AIFF"] = "ON"
        tc.variables["SDLMIXER_WAVE"] = "ON"
        tc.variables["SDLMIXER_VOC"] = "ON"
        tc.variables["SDLMIXER_AU"] = "ON"
        # Heavy optional backends — disable to avoid pulling additional
        # vendored deps / running external/download.sh. Re-enable individually
        # once we add the corresponding Conan recipes.
        tc.variables["SDLMIXER_FLAC"] = "OFF"
        tc.variables["SDLMIXER_GME"] = "OFF"
        tc.variables["SDLMIXER_MOD"] = "OFF"
        tc.variables["SDLMIXER_MP3"] = "OFF"
        tc.variables["SDLMIXER_OGG"] = "OFF"        # Vorbis
        tc.variables["SDLMIXER_OPUS"] = "OFF"
        tc.variables["SDLMIXER_WAVPACK"] = "OFF"
        tc.variables["SDLMIXER_FLUIDSYNTH"] = "OFF"
        # Don't pull any vendored third-party libraries — we don't have
        # the system or Conan packages for them either.
        tc.variables["SDLMIXER_VENDORED"] = "OFF"
        # Don't fail on missing optional deps.
        tc.variables["SDLMIXER_STRICT"] = "OFF"
        # Output.
        tc.variables["SDLMIXER_SHARED"] = "OFF"
        tc.variables["SDLMIXER_STATIC"] = "ON"
        # Skip samples / tests — R34 covers these via our test_package.
        tc.variables["SDLMIXER_TESTS"] = "OFF"
        tc.variables["SDLMIXER_EXAMPLES"] = "OFF"
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
        # SDL3_mixer upstream builds either SDL3_mixer::SDL3_mixer-shared
        # or SDL3_mixer::SDL3_mixer-static. We expose just the static
        # library to consumers as `SDL3_mixer`.
        self.cpp_info.libs = ["SDL3_mixer"]
        self.cpp_info.system_libs = ["pthread"]

    def package_id(self):
        # Bionic libc++ ABI is consistent across OHOS profiles.
        del self.info.settings.compiler.libcxx