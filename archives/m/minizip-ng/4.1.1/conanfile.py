#!/usr/bin/env python3
"""Conan recipe — minizip-ng 4.1.1 (CMake).

minizip-ng is a next-generation zip manipulation library supporting
zlib, bzip2, lzma, zstd, ppmd compression and PKWARE/AES encryption.

Dependencies: zlib, bzip2, openssl, xz (liblzma), zstd
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class MinizipNgConan(ConanFile):
    name = "minizip-ng"
    version = "4.1.1"
    description = "Next-gen zip manipulation library with multi-format compression and encryption support"
    license = "Zlib"
    homepage = "https://github.com/zlib-ng/minizip-ng"
    url = "https://github.com/zlib-ng/minizip-ng"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": False,
        "zlib/*:shared": False,
        "bzip2/*:shared": False,
        "openssl/*:shared": False,
        "xz/*:shared": False,
        "zstd/*:shared": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")
        self.requires("bzip2/1.0.8")
        self.requires("openssl/3.5.6")
        self.requires("xz/5.6.2")
        self.requires("zstd/1.5.7")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Static library by default
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Enable OpenSSL (disabled by default when CMake doesn't detect UNIX on OHOS)
        tc.variables["MZ_OPENSSL"] = "ON"
        # Enable Iconv
        tc.variables["MZ_ICONV"] = "ON"
        # Enable all compression formats (no trimming)
        tc.variables["MZ_ZLIB"] = "ON"
        tc.variables["MZ_BZIP2"] = "ON"
        tc.variables["MZ_LZMA"] = "ON"
        tc.variables["MZ_PPMD"] = "ON"
        tc.variables["MZ_ZSTD"] = "ON"
        tc.variables["MZ_PKCRYPT"] = "ON"
        tc.variables["MZ_WZAES"] = "ON"
        tc.variables["MZ_COMPAT"] = "ON"
        # Disable test builds in conan create
        tc.variables["MZ_BUILD_TESTS"] = "OFF"
        tc.generate()

        # Generate CMakeDeps for dependencies
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
        self.cpp_info.libs = ["minizip", "ppmd"]
        self.cpp_info.set_property("cmake_file_name", "minizip")
        self.cpp_info.set_property("cmake_target_name", "minizip::minizip")
        self.cpp_info.requires = ["zlib::zlib", "bzip2::bzip2", "openssl::openssl", "xz::xz", "zstd::zstd"]
