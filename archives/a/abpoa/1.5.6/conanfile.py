#!/usr/bin/env python3
"""Conan recipe for abpoa — CMake-based build with SIMDE for cross-platform SIMD support."""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy, download, mkdir, rename
from conan.tools.build import check_min_cppstd
import os, stat, shutil


class AbpoaConan(ConanFile):
    name = "abpoa"
    version = "1.5.6"
    description = "abPOA: an SIMD-based C library for fast partial order alignment using adaptive band"
    license = "MIT"
    homepage = "https://github.com/yangao07/abpoa"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Download simde (git submodule) headers for cross-platform SIMD support
        simde_dir = os.path.join(self.source_folder, "include", "simde")
        if not os.path.exists(os.path.join(simde_dir, "simde", "x86", "sse2.h")):
            mkdir(self, simde_dir)
            simde_url = "https://github.com/simd-everywhere/simde/archive/refs/tags/v0.8.2.tar.gz"
            get(self, simde_url, destination=simde_dir, strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # SIMDE: use SIMD Everywhere for cross-platform SIMD on ARM64/OHOS
        tc.variables["CMAKE_C_FLAGS"] = "-DUSE_SIMDE -DSIMDE_ENABLE_NATIVE_ALIASES"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Remove .git and test data from simde installation
        simde_inc = os.path.join(self.package_folder, "include", "simde")
        for root, dirs, files in os.walk(simde_inc, topdown=True):
            if ".git" in dirs:
                dirs.remove(".git")
            if "test" in dirs:
                dirs.remove("test")
            if "docker" in dirs:
                dirs.remove("docker")
            if ".circleci" in dirs:
                dirs.remove(".circleci")
            if ".github" in dirs:
                dirs.remove(".github")
            if ".packit" in dirs:
                dirs.remove(".packit")
            if ".no-test" in dirs:
                dirs.remove(".no-test")
        # Also copy the abpoa.pc.in for pkg-config
        copy(self, "abpoa-1.pc",
             src=os.path.join(self.build_folder),
             dst=os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.libs = ["abpoa"]
        self.cpp_info.requires = ["zlib::zlib"]