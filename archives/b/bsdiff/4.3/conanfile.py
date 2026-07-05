#!/usr/bin/env python3
"""Conan recipe for bsdiff — binary diff/patch tools.

Build system: Makefile (raw make, no configure)
Source: https://www.daemonology.net/bsdiff/
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.build import can_run
from conan.tools.layout import basic_layout
from conan.tools.env import VirtualBuildEnv


class BsdiffConan(ConanFile):
    name = "bsdiff"
    version = "4.3"
    description = "Binary diff/patch tools (bsdiff and bspatch)"
    license = "BSD-2-Clause"
    homepage = "https://www.daemonology.net/bsdiff/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("bzip2/1.0.8")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Get bzip2 paths from the dependency
        bzip2 = self.dependencies["bzip2"]
        bzip2_inc = bzip2.package_folder + "/include"
        bzip2_lib = bzip2.package_folder + "/lib"
        # Fix hardcoded paths in Makefile (patch uses $(HOME)/usr/local/*)
        makefile_path = os.path.join(self.source_folder, "Makefile")
        if os.path.isfile(makefile_path):
            with open(makefile_path, "r") as f:
                content = f.read()
            content = content.replace("$(HOME)/usr/local/include", bzip2_inc)
            content = content.replace("$(HOME)/usr/local/lib", bzip2_lib)
            with open(makefile_path, "w") as f:
                f.write(content)
        # Set build environment
        os.environ["CC"] = os.environ.get("CC", "clang")
        self.run(f"make -C {self.source_folder} -j1")

    def package(self):
        # Binaries are built in source_folder by make
        src = os.path.dirname(self.build_folder) if self.build_folder else self.source_folder
        copy(self, "bsdiff", src, os.path.join(self.package_folder, "bin"))
        copy(self, "bspatch", src, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
