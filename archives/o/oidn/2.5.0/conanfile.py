#!/usr/bin/env python3
"""Conan recipe — oidn (OpenImageDenoise) 2.5.0

Intel's high-performance denoising library for ray tracing rendering.
License: Apache-2.0
Homepage: https://openimagedenoise.github.io

Build requirements:
  - ISPC compiler (>= 1.30.0 recommended; >= 1.22.0 accepted with patch)
    Set ISPC_EXECUTABLE env var or have ispc in PATH.
  - CMake 3.15+
"""
import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class OidnConan(ConanFile):
    name = "oidn"
    version = "2.5.0"
    description = "Intel Open Image Denoise - high-performance denoising library for ray tracing rendering"
    license = "Apache-2.0"
    homepage = "https://openimagedenoise.github.io"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # TBB is a runtime dependency
        self.requires("tbb/2023.0.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["OIDN_DEVICE_CPU"] = "ON"
        tc.variables["OIDN_ARCH"] = "ARM64"
        tc.variables["OIDN_APPS"] = "OFF"
        tc.variables["OIDN_FILTER_RT"] = "ON"
        tc.variables["OIDN_FILTER_RTLIGHTMAP"] = "ON"
        tc.variables["OIDN_INSTALL_DEPENDENCIES"] = "OFF"

        # ISPC: required build tool, not a Conan package
        # Check ISPC_EXECUTABLE env var, then PATH
        ispc_exe = os.environ.get("ISPC_EXECUTABLE", "")
        if not ispc_exe:
            import shutil
            ispc_exe = shutil.which("ispc") or ""
        if ispc_exe:
            tc.variables["ISPC_EXECUTABLE"] = ispc_exe

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
        self.cpp_info.set_property("cmake_file_name", "OpenImageDenoise")
        self.cpp_info.set_property("cmake_target_name", "OpenImageDenoise::OpenImageDenoise")
        self.cpp_info.libs = ["OpenImageDenoise"]
        self.cpp_info.libs += ["OpenImageDenoise_core", "OpenImageDenoise_device_cpu"]
