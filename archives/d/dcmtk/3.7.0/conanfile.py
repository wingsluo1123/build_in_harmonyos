#!/usr/bin/env python3
"""Conan recipe for DCMTK 3.7.0 — CMake projects.

DCMTK (DICOM Toolkit) is a collection of libraries and applications implementing
large parts the DICOM standard.

This template enforces R26: BUILD_SHARED_LIBS=OFF for terminal tools.
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class DcmtkConan(ConanFile):
    name = "dcmtk"
    version = "3.7.0"
    description = "DICOM Toolkit (DCMTK) - libraries and applications for DICOM medical imaging"
    license = "BSD-3-Clause"
    homepage = "https://dcmtk.org"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")
        self.requires("openssl/3.5.6")
        self.requires("libpng/1.6.43")
        self.requires("libtiff/4.6.0")
        self.requires("libjpeg-turbo/3.1.4.1")
        self.requires("libxml2/2.15.3")
        self.requires("openjpeg/2.5.0")
        self.requires("libiconv/1.17")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake does not recognize OHOS as a platform.
        # Set CMAKE_SYSTEM_NAME=Linux so CMake can configure properly.
        # On OHOS devices, binaries run natively (no cross-compilation).
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # Allow try_run() to execute test binaries natively on OHOS
        tc.variables["CMAKE_CROSSCOMPILING_EMULATOR"] = "env"
        # R26: Terminal tools must be statically linked for DevBox deployment
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        # DCMTK-specific CMake variables
        tc.variables["DCMTK_WITH_TIFF"] = "ON"
        tc.variables["DCMTK_WITH_PNG"] = "ON"
        tc.variables["DCMTK_WITH_XML"] = "ON"
        tc.variables["DCMTK_WITH_ZLIB"] = "ON"
        tc.variables["DCMTK_WITH_OPENSSL"] = "ON"
        tc.variables["DCMTK_WITH_OPENJPEG"] = "ON"
        tc.variables["DCMTK_WITH_ICONV"] = "ON"
        tc.variables["DCMTK_WITH_THREADS"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # HarmonyOS: POSIX message queue (mq_*) functions are not available;
        # use Unix domain socket IPC implementation instead
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os in ("Linux", "OHOS"):
            tc.extra_cxxflags.append("-DDCMTK_USE_UNIX_SOCKET_QUEUE")
            tc.extra_cflags.append("-DDCMTK_USE_UNIX_SOCKET_QUEUE")
            tc.variables["DCMTK_INSTALL_CMKDIR"] = "lib/cmake/dcmtk"
        tc.generate()
        # Generate CMakeDeps for find_package() support
        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # DCMTK libraries in dependency order (base first)
        self.cpp_info.libs = [
            "ofstd",
            "oflog",
            "oficonv",
            "dcmdata",
            "dcmiod",
            "dcmect",
            "dcmfg",
            "dcmseg",
            "dcmimgle",
            "dcmimage",
            "dcmjpeg",
            "dcmtkcharls",
            "dcmjpls",
            "dcmnet",
            "dcmtls",
            "dcmdsig",
            "dcmsr",
            "dcmxml",
            "dcmpmap",
            "dcmpstat",
            "dcmqrdb",
            "dcmrt",
            "dcmtract",
            "dcmwlm",
            "cmr",
        ]
