#!/usr/bin/env python3
"""Conan recipe for boost-build (b2 build tool) on OHOS.

boost-build uses a custom build system: bootstrap.sh builds the b2 engine,
then b2 install installs it. This is not an autotools/cmake project.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class BoostBuildConan(ConanFile):
    name = "boost-build"
    version = "1.90.0"
    description = "Boost.Build (b2) - a C++ build system from the Boost project"
    license = "BSL-1.0"
    homepage = "https://github.com/boostorg/build"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)
        # Step 1: Build the b2 engine via bootstrap.sh
        self.run("./bootstrap.sh --cxx=clang++ --cxxflags=-fPIC -O2",
                 cwd=self.source_folder)

        # Step 2: Install b2 using itself
        install_prefix = os.path.join(self.build_folder, "install")
        self.run(f"./b2 install --prefix={install_prefix} toolset=clang",
                 cwd=self.source_folder)

    def package(self):
        install_prefix = os.path.join(self.build_folder, "install")
        copy(self, "*", src=install_prefix, dst=self.package_folder)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.buildenv = ["share/b2/src"]
