#!/usr/bin/env python3
"""Conan recipe for TGUI 1.13.0 on OpenHarmony PC.

TGUI is a cross-platform C++ GUI library. This package uses the SDL_RENDERER
backend with X11 disabled (only affects mouse cursor rendering).
"""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy


class TguiConan(ConanFile):
    name = "tgui"
    version = "1.13.0"
    description = "Cross-platform modern C++ GUI library"
    license = "Zlib"
    homepage = "https://tgui.eu"
    url = "https://github.com/texus/TGUI"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("sdl2_ttf/2.24.0")
        self.requires("freetype/2.14.3.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_BUILD_TYPE"] = str(self.settings.build_type)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["TGUI_BACKEND"] = "SDL_RENDERER"
        tc.variables["TGUI_USE_X11"] = "OFF"  # Disable X11 (only affects mouse cursors)
        tc.variables["TGUI_BUILD_TESTS"] = "OFF"  # Disable upstream tests in package build
        tc.variables["TGUI_BUILD_EXAMPLES"] = "OFF"
        tc.variables["TGUI_BUILD_GUI_BUILDER"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "license.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        component = self.cpp_info.components["tgui"]
        component.libs = ["tgui"]
        component.requires = [
            "sdl2_ttf::sdl2_ttf",
            "freetype::freetype",
        ]
        component.set_property("cmake_target_name", "TGUI::TGUI")
        self.cpp_info.set_property("cmake_file_name", "TGUI")
