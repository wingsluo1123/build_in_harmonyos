#!/usr/bin/env python3
"""Conan recipe — vban g20201011 (CMake)."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class VbanConan(ConanFile):
    name = "vban"
    version = "g20201011"
    description = "Command-line VBAN audio and text stream tools"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/quiniouben/vban"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("vban", "audio", "udp", "network")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # These are the three upstream defaults.  They intentionally remain enabled.
        self.requires("alsa-lib/1.2.16.1")
        self.requires("pulseaudio/17.0.1")
        self.requires("jack/1.9.22")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["WITH_ALSA"] = True
        tc.variables["WITH_PULSEAUDIO"] = True
        tc.variables["WITH_JACK"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        CMake(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = []
