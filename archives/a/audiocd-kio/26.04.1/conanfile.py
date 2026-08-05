#!/usr/bin/env python3
"""Conan recipe — audiocd-kio 26.04.1 (KDE Audio CD KIO slave).

Build system: CMake (KDE Frameworks 6)
Dependencies: KF6Config, KF6I18n, KF6KIO, KF6Solid, KF6WidgetsAddons,
             KCddb6 (libkcddb), Cdparanoia, FLAC, libvorbis, ECM, Qt6

OHOS-specific adaptations (via patches):
  - KCMUtils made optional (kcmutils_generate_desktop_file not available)
  - DocTools disabled (kdoctools_create_handbook not available)
  - lame encoder disabled (library not available)
  - Opus encoder conditionally built
  - Pre-generated kconfig_compiler files for flac/vorbis encoders
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class AudiocdKioConan(ConanFile):
    name = "audiocd-kio"
    version = "26.04.1"
    description = "KDE Audio CD KIO slave — provides audiocd:/ protocol for KDE"
    license = "GPL-2.0-or-later"
    homepage = "https://apps.kde.org/audiocd_kio/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # KDE Framework 6 dependencies
        self.requires("ecm/6.20.0")
        self.requires("qtbase/6.11.1")
        self.requires("flac/1.4.3")
        self.requires("libvorbis/1.3.7")
        # Resolve libogg version conflict between flac (1.3.5) and libvorbis (1.3.6)
        self.requires("libogg/1.3.6", override=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # Add Qt6 bin to CMAKE_PROGRAM_PATH so find_program can find qtpaths6
        qt_bin = os.path.join(self.dependencies["qtbase"].package_folder, "bin")
        tc.variables["CMAKE_PROGRAM_PATH"] = qt_bin
        # Set CMAKE_PREFIX_PATH to include all dependency package folders
        # so cmake can find the real cmake config files (not just CMakeDeps stubs)
        prefix_paths = []
        for dep_name in ["qtbase", "ecm", "flac", "libvorbis", "libogg"]:
            if dep_name in self.dependencies:
                prefix_paths.append(self.dependencies[dep_name].package_folder)
        if prefix_paths:
            tc.cache_variables["CMAKE_PREFIX_PATH"] = ";".join(prefix_paths)
        tc.generate()
        # Generate CMakeDeps for cmake find_package support
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["kio_audiocd", "audiocdplugins"]
        self.cpp_info.set_property("cmake_file_name", "AudiocdKio")
