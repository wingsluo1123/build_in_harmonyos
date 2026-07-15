#!/usr/bin/env python3
"""Conan recipe for lmdbxx — C++17 header-only wrapper for LMDB.

lmdbxx provides a single header file (lmdb++.h) that wraps the LMDB C API.
Build step is a no-op (header-only). Package step copies the header.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LmdbxxConan(ConanFile):
    name = "lmdbxx"
    version = "1.0.0"
    description = "C++17 wrapper for LMDB database"
    license = "Public-Domain"
    homepage = "https://github.com/hoytech/lmdbxx"
    url = ""  # CI fills this

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("lmdb/0.9.32")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(self, "lmdb++.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.requires = ["lmdb::lmdb"]
