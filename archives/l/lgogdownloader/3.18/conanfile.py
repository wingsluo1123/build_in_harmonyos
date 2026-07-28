#!/usr/bin/env python3
"""Conan recipe — lgogdownloader 3.18 (CMake application)"""
import os, glob

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LgogdownloaderConan(ConanFile):
    name = "lgogdownloader"
    version = "3.18"
    description = "LGOGDownloader — 非官方 GOG.com 游戏下载器（CMake 应用，鸿蒙 PC 适配）"
    license = "Unlicense"
    homepage = "https://github.com/Sude-/lgogdownloader"
    url = ""
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("boost/1.84.0")
        self.requires("jsoncpp/1.9.8")
        self.requires("libcurl/8.5.0")
        self.requires("librhash/1.4.4")
        self.requires("tidy-html5/5.8.0")
        self.requires("tinyxml2/10.0.0")
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["USE_QT_GUI"] = "OFF"
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
        if self.settings.os == "OHOS":
            bindir = os.path.join(self.package_folder, "bin")
            for exe in glob.glob(os.path.join(bindir, "*")):
                if os.path.isfile(exe) and not os.path.islink(exe):
                    objcopy = "/data/service/hnp/bin/llvm-objcopy"
                    signer = "/data/service/hnp/bin/binary-sign-tool"
                    self.run(f'{objcopy} --remove-section .codesign "{exe}" 2>/dev/null || true')
                    self.run(f'{signer} sign -inFile "{exe}" -outFile "{exe}" -selfSign 1')

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
