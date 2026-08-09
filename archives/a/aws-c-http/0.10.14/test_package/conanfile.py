#!/usr/bin/env python3
"""Conan test_package for aws-c-http 0.10.14 — Conan L1 official test."""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AwschttpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("aws-c-common/0.14.3")
        self.requires("aws-c-io/0.26.3")
        self.requires("aws-c-compression/0.3.2")
        self.requires("aws-c-cal/0.9.13")
        self.requires("s2n/1.7.3")
        self.requires("openssl/3.5.6.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        import os
        cmake = CMake(self)
        prefix_paths = [d.package_folder for d in self.dependencies.values() if hasattr(d, 'package_folder') and d.package_folder]
        vars_dict = {"CMAKE_PREFIX_PATH": ";".join(prefix_paths)} if prefix_paths else {}
        for d in self.dependencies.values():
            if hasattr(d, 'package_folder') and d.package_folder:
                s2n_cmake = os.path.join(d.package_folder, "lib", "cmake", "s2n")
                if os.path.isdir(s2n_cmake):
                    vars_dict["s2n_DIR"] = s2n_cmake
                    break
        cmake.configure(variables=vars_dict)
        cmake.build()

    def test(self):
        self.run("ctest --output-on-failure", env="conanrun")
