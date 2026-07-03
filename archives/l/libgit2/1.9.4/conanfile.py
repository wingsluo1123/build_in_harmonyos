#!/usr/bin/env python3
"""Conan recipe — libgit2 1.9.4 (CMake project).

libgit2 is NOT a system same-name library (R26): default dynamic linking, managed by Conan.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.env import Environment


class Libgit2Conan(ConanFile):
    name = "libgit2"
    version = "1.9.4"
    description = "Lightweight cross-platform Git core library implementation"
    license = "MIT"
    homepage = "https://libgit2.org/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6@ohpcd/stable")
        self.requires("zlib/1.3.1@ohpcd/stable")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: libgit2 is NOT a system same-name library; default dynamic linking managed by Conan
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["BUILD_TESTS"] = "OFF"
        # Explicitly set HTTPS/SHA backend to OpenSSL (avoid autodetect failure)
        tc.variables["USE_HTTPS"] = "OpenSSL"
        tc.variables["USE_SHA256"] = "OpenSSL"
        # E001/E092: Fix compiler path when profile's path doesn't exist on this system
        cc = os.environ.get("CC", "")
        cxx = os.environ.get("CXX", "")
        if cc:
            tc.variables["CMAKE_C_COMPILER"] = cc
        if cxx:
            tc.variables["CMAKE_CXX_COMPILER"] = cxx
        # Set OPENSSL_ROOT_DIR and ZLIB_ROOT for find_package(OpenSSL)/find_package(ZLIB)
        # Without CMakeDeps, CMake's built-in FindOpenSSL.cmake will respect these
        prefix_paths = []
        for name, dep in self.dependencies.items():
            pf = getattr(dep, "package_folder", None)
            if pf:
                if "openssl" in str(name).lower():
                    tc.variables["OPENSSL_ROOT_DIR"] = pf
                    tc.variables["OPENSSL_USE_STATIC_LIBS"] = "ON"
                elif "zlib" in str(name).lower():
                    tc.variables["ZLIB_ROOT"] = pf
                prefix_paths.append(pf)
        if prefix_paths:
            tc.variables["CMAKE_PREFIX_PATH"] = ";".join(prefix_paths)
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
        self.cpp_info.libs = ["git2"]
