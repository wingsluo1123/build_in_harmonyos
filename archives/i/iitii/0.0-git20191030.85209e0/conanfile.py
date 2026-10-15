#!/usr/bin/env python3
"""Conan recipe — iitii 0.0-git20191030.85209e0 (header-only interval index).

iitii is a header-only C++14 library: implicit interval tree with
interpolation index for begin/end position intervals (genomic annotations).
Core header is src/iitii.h; it includes ips4o.hpp (parallel sort) and
mmappable_vector.h (mmap allocator) from Conan requirements. The upstream
CMakeLists additionally builds a memmapped CLI tool (needs args + OpenMP),
which this header-library package does not build or ship.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class IitiiConan(ConanFile):
    name = "iitii"
    version = "0.0-git20191030.85209e0"
    description = "Implicit Interval Tree with Interpolation Index (header-only C++14 interval index)"
    license = "Apache-2.0"
    homepage = "https://github.com/mlin/iitii"
    url = "https://github.com/mlin/iitii"
    topics = ("interval-tree", "genomics", "header-only", "cpp14")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ips4o/0.0-git22069381cc")
        self.requires("mmap_allocator/3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(self, "iitii.h", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "iitii")
        self.cpp_info.set_property("cmake_target_name", "iitii::iitii")
