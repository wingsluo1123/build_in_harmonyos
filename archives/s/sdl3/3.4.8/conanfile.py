#!/usr/bin/env python3
"""Conan recipe for SDL 3.4.8."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class Sdl3Conan(ConanFile):
    name = "sdl3"
    version = "3.4.8"
    description = "Cross-platform development library for audio, input, and graphics"
    license = "Zlib"
    homepage = "https://www.libsdl.org/"
    url = "https://github.com/libsdl-org/SDL"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("SDL3 is supported on Linux and OHOS")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        if self.settings.os == "OHOS":
            toolchain = CMakeToolchain(self, generator="Ninja")
        else:
            toolchain = CMakeToolchain(self)

        toolchain.variables["SDL_SHARED"] = bool(self.options.shared)
        toolchain.variables["SDL_STATIC"] = not bool(self.options.shared)
        toolchain.variables["SDL_TEST_LIBRARY"] = False
        toolchain.variables["SDL_TESTS"] = False
        toolchain.variables["SDL_INSTALL_TESTS"] = False
        toolchain.variables["SDL_EXAMPLES"] = False
        toolchain.variables["SDL_INSTALL_DOCS"] = False
        toolchain.variables["SDL_INSTALL_CPACK"] = False
        toolchain.variables["SDL_UNINSTALL"] = False
        toolchain.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(
            self.options.get_safe("fPIC", True)
        )

        if self.settings.os == "OHOS":
            toolchain.variables["SDL_PTHREADS"] = True
            toolchain.variables["SDL_TRAY"] = False
            toolchain.variables["SDL_DBUS"] = False
            toolchain.variables["SDL_LIBURING"] = False
            toolchain.variables["SDL_IBUS"] = False
            toolchain.variables["SDL_ALSA"] = False
            toolchain.variables["SDL_JACK"] = False
            toolchain.variables["SDL_PIPEWIRE"] = False
            toolchain.variables["SDL_PULSEAUDIO"] = False
            toolchain.variables["SDL_SNDIO"] = False
            toolchain.variables["SDL_X11"] = False
            toolchain.variables["SDL_WAYLAND"] = False
            toolchain.variables["SDL_RPI"] = False
            toolchain.variables["SDL_ROCKCHIP"] = False
            toolchain.variables["SDL_KMSDRM"] = False
            toolchain.variables["SDL_HIDAPI"] = False
            toolchain.variables["SDL_LIBUDEV"] = False
            toolchain.variables["SDL_OPENGL"] = False
            toolchain.variables["SDL_OPENGLES"] = False
            toolchain.variables["SDL_VULKAN"] = False
            toolchain.variables["SDL_DLOPEN_NOTES"] = False
            toolchain.variables["SDL_RPATH"] = False

        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        CMake(self).install()
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["SDL3"]
        self.cpp_info.set_property("cmake_file_name", "SDL3")
        self.cpp_info.set_property("cmake_target_name", "SDL3::SDL3")
        if not self.options.shared and self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs.extend(["m", "pthread", "dl"])
