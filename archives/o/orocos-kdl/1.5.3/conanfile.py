#!/usr/bin/env python3
"""Conan recipe for orocos-kdl 1.5.3 — Orocos Kinematics and Dynamics Library.

Builds the orocos_kdl subdirectory from the monorepo.
Requires Eigen3 (header-only, downloaded directly).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy, save, download
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import os


class OrocoskdlConan(ConanFile):
    name = "orocos-kdl"
    version = "1.5.3"
    description = "Orocos Kinematics and Dynamics Library — real-time usable kinematics and dynamics code"
    license = "BSD-2-Clause"
    homepage = "https://orocos.org/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        # Download orocos-kdl source
        get(self, **self.conan_data["sources"], strip_root=True)
        # Download Eigen3 (header-only) into the build environment
        eigen_url = "https://gitlab.com/libeigen/eigen/-/archive/3.4.0/eigen-3.4.0.tar.gz"
        eigen_dir = os.path.join(self.source_folder, "_eigen")
        get(self, eigen_url, destination=eigen_dir, strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: System-name libraries default to static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Point to the downloaded Eigen3 headers
        eigen_include = os.path.join(self.source_folder, "_eigen")
        tc.variables["EIGEN3_INCLUDE_DIR"] = eigen_include
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Source is in the orocos_kdl subdirectory of the monorepo
        cmake = CMake(self)
        cmake.configure(build_script_folder="orocos_kdl")
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder="orocos_kdl")
        cmake.install()
        # Copy Eigen3 headers into the package (KDL headers depend on Eigen3)
        eigen_src = os.path.join(self.source_folder, "_eigen", "Eigen")
        eigen_dst = os.path.join(self.package_folder, "include", "Eigen")
        if os.path.isdir(eigen_src) and not os.path.isdir(eigen_dst):
            copy(self, "*", src=os.path.dirname(eigen_src), dst=os.path.join(self.package_folder, "include"))
        # Copy license file
        for lic in ["COPYING", "LICENSE", "LICENSE.txt"]:
            src = os.path.join(self.source_folder, lic)
            if os.path.exists(src):
                copy(self, lic, src=os.path.dirname(src), dst=os.path.join(self.package_folder, "licenses"))
                break

    def package_info(self):
        self.cpp_info.libs = ["orocos-kdl"]
        self.cpp_info.includedirs = ["include"]
        # CMake config files are installed to share/orocos_kdl/cmake/
        self.cpp_info.set_property("cmake_file_name", "orocos-kdl")
        self.cpp_info.set_property("cmake_target_name", "orocos-kdl::orocos-kdl")