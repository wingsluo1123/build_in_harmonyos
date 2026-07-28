#!/usr/bin/env python3
"""Conan recipe — tinyxml2 10.0.0 (CMake)"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Tinyxml2Conan(ConanFile):
    name = "tinyxml2"
    version = "10.0.0"
    description = "A simple, small, efficient C++ XML parser（轻量 XML 解析库，CMake 构建，鸿蒙 PC 适配）"
    license = "Zlib"
    homepage = "https://github.com/leethomason/tinyxml2"
    url = ""
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["tinyxml2_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["tinyxml2_BUILD_TESTING"] = "OFF"
        if self.settings.os == "OHOS":
            for lang in ("C", "CXX"):
                tc.variables[f"CMAKE_SHARED_LIBRARY_SONAME_{lang}_FLAG"] = "-Wl,-soname,"
                tc.variables[f"CMAKE_SHARED_LIBRARY_RUNTIME_{lang}_FLAG"] = "-Wl,-rpath,"
                tc.variables[f"CMAKE_SHARED_LIBRARY_RUNTIME_{lang}_FLAG_SEP"] = ":"
                tc.variables[f"CMAKE_SHARED_LIBRARY_RPATH_LINK_{lang}_FLAG"] = "-Wl,-rpath-link,"
            tc.variables["CMAKE_BUILD_RPATH_USE_ORIGIN"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        if self.settings.os == "OHOS" and self.options.shared:
            import glob, shutil
            libdir = os.path.join(self.package_folder, "lib")
            sos = glob.glob(os.path.join(libdir, "**", "*.so*"), recursive=True)
            objcopy = "/data/service/hnp/bin/llvm-objcopy"
            signer = "/data/service/hnp/bin/binary-sign-tool"
            for so in sos:
                if os.path.islink(so):
                    continue
                self.run(f'{objcopy} --remove-section .codesign "{so}" 2>/dev/null || true')
                self.run(f'{signer} sign -inFile "{so}" -outFile "{so}" -selfSign 1')

    def package_info(self):
        self.cpp_info.libs = ["tinyxml2"]
        self.cpp_info.set_property("cmake_file_name", "tinyxml2")
        self.cpp_info.set_property("cmake_target_name", "tinyxml2::tinyxml2")
        self.cpp_info.set_property("pkg_config_name", "tinyxml2")
