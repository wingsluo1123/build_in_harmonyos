#!/usr/bin/env python3
"""Conan recipe for libtheora 1.1.1.

libtheora is a free, patent-unencumbered video codec derived from On2's VP3.
This recipe replaces the upstream autotools build system with a CMake-based
build for OpenHarmony cross-compilation compatibility.

Source: https://gitlab.xiph.org/xiph/theora
"""

import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import get, export_conandata_patches


class LibtheoraConan(ConanFile):
    name = "libtheora"
    version = "1.1.1"
    description = "Theora video codec library (free, patent-unencumbered)"
    license = "BSD-3-Clause"
    homepage = "https://xiph.org/theora/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libogg/1.3.6")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Build static libraries
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        # Copy our custom CMakeLists.txt to replace the autotools build system.
        # The original source has no CMakeLists.txt (uses autotools), so this
        # is a full-file replacement, not a diff patch.
        cmake_patch = os.path.join(self.export_sources_folder, "patches", "CMakeLists.txt")
        shutil.copy2(cmake_patch, os.path.join(self.source_folder, "CMakeLists.txt"))

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # theoradec component
        self.cpp_info.components["theoradec"].libs = ["theoradec"]
        self.cpp_info.components["theoradec"].requires = ["libogg::libogg"]
        self.cpp_info.components["theoradec"].set_property("cmake_file_name", "theoradec")
        self.cpp_info.components["theoradec"].set_property("cmake_target_name", "theoradec::theoradec")
        self.cpp_info.components["theoradec"].set_property("pkg_config_name", "theoradec")

        # theoraenc component
        self.cpp_info.components["theoraenc"].libs = ["theoraenc"]
        self.cpp_info.components["theoraenc"].requires = ["theoradec", "libogg::libogg"]
        self.cpp_info.components["theoraenc"].set_property("cmake_file_name", "theoraenc")
        self.cpp_info.components["theoraenc"].set_property("cmake_target_name", "theoraenc::theoraenc")
        self.cpp_info.components["theoraenc"].set_property("pkg_config_name", "theoraenc")

        # theora combined component (includes both decoder and encoder)
        self.cpp_info.components["theora"].libs = ["theora"]
        self.cpp_info.components["theora"].requires = ["theoradec", "theoraenc", "libogg::libogg"]
        self.cpp_info.components["theora"].set_property("cmake_file_name", "theora")
        self.cpp_info.components["theora"].set_property("cmake_target_name", "theora::theora")
        self.cpp_info.components["theora"].set_property("pkg_config_name", "theora")
