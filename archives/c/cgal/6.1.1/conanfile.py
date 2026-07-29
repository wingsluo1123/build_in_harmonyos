#!/usr/bin/env python3
"""Conan recipe - CGAL 6.1.1 (header-only core package)."""

import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class CgalConan(ConanFile):
    name = "cgal"
    version = "6.1.1"
    description = "Computational Geometry Algorithms Library headers"
    license = "GPL-3.0-or-later OR LGPL-3.0-or-later"
    homepage = "https://www.cgal.org/"
    url = "https://github.com/CGAL/cgal"

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def package(self):
        copy(
            self,
            "include/CGAL/*",
            src=self.source_folder,
            dst=self.package_folder,
        )
        copy(
            self,
            "LICENSE*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("cmake_file_name", "CGAL")
        self.cpp_info.set_property("cmake_target_name", "CGAL::CGAL")
