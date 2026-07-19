#!/usr/bin/env python3
"""Conan recipe for sdl12-compat 1.2.68."""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class Sdl12CompatConan(ConanFile):
    name = "sdl12-compat"
    version = "1.2.68"
    description = "SDL 1.2 compatibility layer on top of SDL2"
    license = "Zlib"
    homepage = "https://github.com/libsdl-org/sdl12-compat"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("SDL2/2.30.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["SDL12TESTS"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        if self.settings.os == "OHOS" and bool(self.options.shared):
            self._sign_shared_libs()

    def package_info(self):
        self.cpp_info.libs = ["SDL-1.2"]
        self.cpp_info.includedirs = ["include/SDL"]
        self.cpp_info.requires = ["SDL2::SDL2"]
        self.cpp_info.set_property("cmake_file_name", "SDL")
        self.cpp_info.set_property("cmake_target_name", "SDL::SDL")

    def _sign_shared_libs(self):
        libraries = glob.glob(os.path.join(self.package_folder, "lib", "*.so*"))
        for library in libraries:
            if os.path.islink(library):
                continue
            self.run(
                f'/data/service/hnp/bin/llvm-objcopy --remove-section .codesign "{library}" '
                "2>/dev/null || true"
            )
            self.run(
                f'/data/service/hnp/bin/binary-sign-tool sign -inFile "{library}" '
                f'-outFile "{library}" -selfSign 1'
            )
