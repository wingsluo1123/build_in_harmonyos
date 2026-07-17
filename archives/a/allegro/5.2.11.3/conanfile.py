#!/usr/bin/env python3
"""Conan recipe — allegro 5.2.11.3 (CMake)"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AllegroConan(ConanFile):
    name = "allegro"
    version = "5.2.11.3"
    description = "Cross-platform game development library"
    license = "Zlib"
    homepage = "https://liballegro.org/"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Allegro uses its own SHARED option, not BUILD_SHARED_LIBS
        tc.variables["SHARED"] = "ON" if self.options.shared else "OFF"
        tc.variables["WANT_X11"] = "OFF"
        tc.variables["ALLEGRO_UNIX"] = "1"
        tc.variables["WANT_EXAMPLES"] = "OFF"
        tc.variables["WANT_POPUP_EXAMPLES"] = "OFF"
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
        # Allegro appends "-static" suffix to static library names
        suffix = "" if self.options.shared else "-static"
        self.cpp_info.libs = [
            f"allegro{suffix}",
            f"allegro_acodec{suffix}",
            f"allegro_audio{suffix}",
            f"allegro_color{suffix}",
            f"allegro_font{suffix}",
            f"allegro_image{suffix}",
            f"allegro_main{suffix}",
            f"allegro_memfile{suffix}",
            f"allegro_primitives{suffix}",
        ]
        # System libraries required by allegro on Unix-like platforms
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl", "rt"]
