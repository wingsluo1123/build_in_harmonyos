#!/usr/bin/env python3
"""Conan recipe for pgexporter 0.8.0 — Prometheus exporter for PostgreSQL.

Adapted for HarmonyOS/OpenHarmony aarch64 platform.
Built as static library to avoid fPIC issues with static-only system deps.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class PgexporterConan(ConanFile):
    name = "pgexporter"
    version = "0.8.0"
    description = "Prometheus exporter for PostgreSQL"
    license = "BSD-3-Clause"
    homepage = "https://github.com/pgexporter/pgexporter"
    url = "https://github.com/pgexporter/pgexporter"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libev/4.33")
        self.requires("libyaml/0.2.5")
        self.requires("openssl/3.5.6")
        self.requires("zlib/1.3.1")
        self.requires("bzip2/1.0.8")
        self.requires("lz4/1.10.0")
        self.requires("zstd/1.5.7")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
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
        self.cpp_info.libs = ["pgexporter"]
        self.cpp_info.bindirs = ["bin"]
