#!/usr/bin/env python3
"""Conan recipe for baresip 4.9.0 — CMake build system.

baresip is a modular SIP user agent (audio/video) built on top of libre (re).
Build system: CMake

Key design:
  - re/4.9.0 is a Conan dependency (published to ohpcd remote).
  - Patch 0001 modifies CMakeLists.txt to use Conan CMakeDeps variables
    (re_INCLUDE_DIRS, re::re target) instead of FindRE.cmake's uppercase
    RE_INCLUDE_DIRS / RE_LIBRARIES. This is needed because Conan's
    CMakeToolchain sets CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON, which causes
    find_package(RE) to use re-config.cmake instead of FindRE.cmake.
  - baresip is modular: modules needing unavailable system libs (ALSA,
    PulseAudio, FFmpeg, etc.) auto-skip via find_package() + return().
    We explicitly set MODULES to only include dependency-free modules.
  - R9:  Use -j1 (OHOS parallel constraint).
  - R32: settings.os check uses `in ("Linux", "OHOS")`.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class BaresipConan(ConanFile):
    name = "baresip"
    version = "4.9.0"
    description = "Modular SIP user agent with audio and video support"
    license = "BSD-3-Clause"
    homepage = "https://github.com/baresip/baresip"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # re (libre) 4.9.0 published on ohpcd remote
        # recipe rev c8fff1f0ad8a07baf8461e92744e4539
        self.requires("re/4.9.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # CMakeDeps generates re-config.cmake / openssl-config.cmake
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # R32: settings.os check must use `in ("Linux", "OHOS")`
        if self.settings.os not in ("Linux", "OHOS"):
            raise Exception(f"Unsupported OS: {self.settings.os}")

        # Static build to avoid polluting system lib paths (R26 spirit)
        shared = bool(self.options.shared)
        tc.variables["STATIC"] = "ON" if not shared else "OFF"

        # Only build modules with no external system dependencies.
        # Modules needing ALSA/PulseAudio/FFmpeg/etc. auto-skip, but
        # we explicitly list the safe set for reproducibility.
        tc.variables["MODULES"] = (
            "account;aufile;auconv;augain;auresamp;ausine;contact;"
            "debug_cmd;echo;g711;libg722;g722;g7221;httpreq;ice;"
            "in_band_dtmf;l16;menu;mixausrc;mixminus;mqtt;httpd;mwi;"
            "natpmp;pcp;plc;presence;rtcpsummary;selfview;serreg;"
            "snapshot;stdio;stun;turn;uuid;vidbridge;vidinfo;"
            "vumeter;fakevideo"
        )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # R9: Use -j1 for parallel constraint on OHOS platform
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["-j1"])

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["baresip"]
        # re (libre) is a transitive Conan dependency
        # System libs needed for linking
        self.cpp_info.system_libs = ["dl", "pthread", "m"]
