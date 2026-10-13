#!/usr/bin/env python3
"""Conan recipe for TGUI 1.13.0 on OpenHarmony PC.

TGUI is a cross-platform C++ GUI library. This package uses the SDL_RENDERER
backend with X11 disabled (only affects mouse cursor rendering).

OpenHarmony platform handling: TGUI's cmake/Config.cmake only recognises
Windows/Android/Linux/BSD/macOS and aborts with "Unsupported CMAKE_SYSTEM_NAME
value" for anything else. CMAKE_SYSTEM_NAME is therefore left to the toolchain
(which reports the real target system, "HarmonyOS", for os=OHOS), and
patches/0001 adds the missing HarmonyOS branch mapping it onto TGUI's existing
Linux/BSD code path (TGUI_OS_LINUX) - the same ABI layer HarmonyOS implements.
"""
import os
import shutil
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
        self.requires("sdl2/2.30.10")
        self.requires("sdl2_ttf/2.24.0")
        self.requires("freetype/2.14.3.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # The OHOS sandbox denies make's hardcoded SHELL=/bin/sh, so a clean
        # Makefiles build dies inside CMake's configure-stage try_compile
        # ("Check for working CXX compiler: ... - broken"). Ninja execs the
        # compiler directly, keeping configure and build working on every
        # worker (E346).
        generator = "Ninja" if str(self.settings.os) == "OHOS" else None
        tc = CMakeToolchain(self, generator=generator)
        if generator == "Ninja":
            # The Ninja generator probes `ninja --version` through PATH, where a
            # user-path shim is denied by the sandbox; pin the system ninja.
            ninja = "/data/service/hnp/bin/ninja"
            tc.variables["CMAKE_MAKE_PROGRAM"] = (
                ninja if os.path.isfile(ninja) else (shutil.which("ninja") or "ninja")
            )
        tc.variables["CMAKE_BUILD_TYPE"] = str(self.settings.build_type)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["TGUI_BACKEND"] = "SDL_RENDERER"
        tc.variables["TGUI_USE_X11"] = "OFF"  # Disable X11 (only affects mouse cursors)
        tc.variables["TGUI_BUILD_TESTS"] = "OFF"  # Disable upstream tests in package build
        tc.variables["TGUI_BUILD_EXAMPLES"] = "OFF"
        tc.variables["TGUI_BUILD_GUI_BUILDER"] = "OFF"
        if str(self.settings.os) == "OHOS":
            # CMAKE_SYSTEM_NAME is intentionally not overridden: patches/0001
            # keys on it to enable TGUI's HarmonyOS support, and forcing
            # "Linux" here made that branch unreachable (the toolchain reports
            # the real system name of the target). CMake cannot infer the
            # processor of a HarmonyOS target, so only that one is pinned.
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
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
            "sdl2::sdl2",
            "sdl2_ttf::sdl2_ttf",
            "freetype::freetype",
        ]
        component.set_property("cmake_target_name", "TGUI::TGUI")
        self.cpp_info.set_property("cmake_file_name", "TGUI")
