#!/usr/bin/env python3
"""Conan recipe for DCMTK 3.7.0 — CMake projects.

DCMTK (DICOM Toolkit) is a collection of libraries and applications implementing
large parts the DICOM standard.

This template enforces R26: BUILD_SHARED_LIBS=OFF for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


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
        # All dependencies should use @ohpcd/stable format (R27) once published.
        # Currently no @ohpcd/stable packages are available in the remote yet,
        # so all dependencies (zlib, openssl, libpng, libtiff, libjpeg-turbo,
        # libxml2, openjpeg, libiconv) are pre-installed system libraries
        # found via CMAKE_PREFIX_PATH and *_ROOT variables in generate().
        # TODO: Once @ohpcd/stable packages are uploaded, migrate to:
        # self.requires("zlib/1.3.1@ohpcd/stable")
        # self.requires("openssl/3.5.6@ohpcd/stable")
        # self.requires("libpng/1.6.43@ohpcd/stable")
        # self.requires("libtiff/4.6.0@ohpcd/stable")
        # self.requires("libjpeg-turbo/3.1.4.1@ohpcd/stable")
        # self.requires("libxml2/2.15.3@ohpcd/stable")
        # self.requires("openjpeg/2.5.0@ohpcd/stable")
        # self.requires("libiconv/1.17@ohpcd/stable")
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMAKE_SYSTEM_NAME=Linux is set via user_toolchain in the
        # local Conan profile (ohos-aarch64-local). The user_toolchain also
        # sets CMAKE_CROSSCOMPILING_EMULATOR so try_run() can execute
        # test binaries natively on the DevBox.
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
            # DCMTK_USE_UNIX_SOCKET_QUEUE is a preprocessor define, not a CMake option
            tc.extra_cxxflags.append("-DDCMTK_USE_UNIX_SOCKET_QUEUE")
            tc.extra_cflags.append("-DDCMTK_USE_UNIX_SOCKET_QUEUE")
            tc.variables["DCMTK_INSTALL_CMKDIR"] = "lib/cmake/dcmtk"
            # System libraries installed to ~/usr/local (pre-compiled deps)
            # Set find_package root variables for each library
            home = os.environ.get("HOME", "")
            if home:
                prefix = os.path.join(home, "usr", "local")
                libdir = os.path.join(prefix, "lib")
                incdir = os.path.join(prefix, "include")
                # Help CMake find_package() locate system-installed libraries
                # Set individual cache variables that FindOpenSSL.cmake respects
                tc.variables["OPENSSL_ROOT_DIR"] = prefix
                tc.variables["OPENSSL_INCLUDE_DIR"] = incdir
                tc.variables["OPENSSL_CRYPTO_LIBRARY"] = os.path.join(libdir, "libcrypto.so")
                tc.variables["OPENSSL_SSL_LIBRARY"] = os.path.join(libdir, "libssl.so")
                tc.variables["ZLIB_ROOT"] = prefix
                tc.variables["PNG_ROOT"] = prefix
                tc.variables["TIFF_ROOT"] = prefix
                tc.variables["JPEG_ROOT"] = prefix
                tc.variables["LIBXML2_ROOT_DIR"] = prefix
                tc.variables["OPENJPEG_ROOT"] = prefix
                tc.variables["ICONV_ROOT"] = prefix
                # Also set CMAKE_PREFIX_PATH as fallback
                tc.variables["CMAKE_PREFIX_PATH"] = prefix
                tc.variables["CMAKE_LIBRARY_PATH"] = libdir
                # Ensure linker can find shared libraries at runtime
                tc.extra_exelinkflags.append(f"-L{libdir}")
                tc.extra_exelinkflags.append("-lssl -lcrypto")
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
