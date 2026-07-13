#!/usr/bin/env python3
"""Conan recipe for httping — ping-like tool for HTTP requests.

httping is a CLI tool for measuring HTTP request latency.
Uses CMake build system; SSL, TUI, FFTW3, gettext are optional features.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import cross_building
import os


class HttpingConan(ConanFile):
    name = "httping"
    version = "4.4.0"
    description = "Ping-like tool for HTTP requests"
    license = "AGPL-3.0-only"
    homepage = "https://github.com/folkertvanheusden/HTTPing"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

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
        # Minimal build: disable all optional features
        tc.variables["USE_SSL"] = "OFF"
        tc.variables["USE_TUI"] = "OFF"
        tc.variables["USE_GETTEXT"] = "OFF"
        tc.variables["USE_FFTW3"] = "OFF"
        # Release build
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
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
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
