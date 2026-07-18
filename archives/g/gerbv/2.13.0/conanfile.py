#!/usr/bin/env python3
"""Conan recipe for gerbv 2.13.0 — Gerber RS-274X file viewer.

Build system: CMake (the project has transitioned from Autotools)
License: GPL-2.0
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class GerbvConan(ConanFile):
    name = "gerbv"
    version = "2.13.0"
    description = "gerbv - A Free/Open Source Gerber RS-274X file viewer"
    license = "GPL-2.0"
    homepage = "https://gerbv.github.io/"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # gerbv requires GTK+ 2.x (or 3.x with modifications)
        self.requires("glib/2.80")
        self.requires("cairo/1.18")
        self.requires("libxml2/2.13")
        # gtk2/2.24 is required but not yet published to OHOS conan repo
        # self.requires("gtk/2.24")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0077"] = "NEW"
        tc.generate()
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
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
