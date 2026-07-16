#!/usr/bin/env python3
"""Conan recipe for torchvision 0.28.0 (CMake).

Builds the torchvision C++ extension library against libtorch.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.layout import basic_layout


class TorchvisionConan(ConanFile):
    name = "torchvision"
    version = "0.28.0"
    description = "Datasets, Transforms and Models for computer vision (C++ extension)"
    license = "MIT"
    homepage = "https://github.com/pytorch/vision"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "with_png": [True, False],
        "with_jpeg": [True, False],
        "with_webp": [True, False],
    }
    default_options = {
        "shared": True,
        "with_png": False,
        "with_jpeg": False,
        "with_webp": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libtorch must be published to ohpcd first (R36)
        # self.requires("libtorch/2.9.0")
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["WITH_PNG"] = self.options.with_png
        tc.variables["WITH_JPEG"] = self.options.with_jpeg
        tc.variables["WITH_WEBP"] = self.options.with_webp
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["CMAKE_CROSSCOMPILING"] = "OFF"
        tc.variables["CMAKE_LINK_WHAT_YOU_USE"] = "OFF"
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
        self.cpp_info.libs = ["torchvision"]
        self.cpp_info.requires = ["torch::torch"]  # depends on libtorch
