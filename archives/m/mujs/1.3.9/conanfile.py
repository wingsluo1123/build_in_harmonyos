#!/usr/bin/env python3
"""Conan recipe — mujs 1.3.9 (Makefile)"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MujsConan(ConanFile):
    name = "mujs"
    version = "1.3.9"
    description = "MuJS is a lightweight JavaScript interpreter designed for embedding in other programs"
    license = "MIT"
    homepage = "https://mujs.com/"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # mujs uses a simple Makefile; run in source folder
        self.run(f"make -C {self.source_folder} release HAVE_READLINE=no -j1")

    def package(self):
        # Copy header
        copy(self, "mujs.h", self.source_folder, os.path.join(self.package_folder, "include"))

        # Copy libraries from build/release/
        build_release = os.path.join(self.source_folder, "build", "release")
        if self.options.shared:
            copy(self, "*.so*", build_release, os.path.join(self.package_folder, "lib"))
        else:
            copy(self, "*.a", build_release, os.path.join(self.package_folder, "lib"))

        # Copy executables
        copy(self, "mujs", build_release, os.path.join(self.package_folder, "bin"))
        copy(self, "mujs-pp", build_release, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["mujs"]
        if not self.options.shared:
            self.cpp_info.system_libs = ["m"]
