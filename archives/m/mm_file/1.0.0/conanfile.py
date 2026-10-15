#!/usr/bin/env python3
"""Conan recipe — mm_file 1.0.0 (C++11 header-only memory-mapped files).

mm_file is a self-contained, header-only implementation of memory-mapped
files in C++ for both reading and writing (mm::file_source / mm::file_sink),
offering the capability of boost::mapped_file without the boost dependency.

This recipe packages the single public header include/mm_file/mm_file.hpp.
No compilation is required (header-only); the library uses only POSIX
syscalls (mmap/munmap/open/fstat/close/posix_madvise) — no third-party
runtime dependencies.

R32 note: no settings.os branch is needed — nothing is compiled, and the
header is portable across Linux and OHOS (both provide the POSIX mmap API).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MmFileConan(ConanFile):
    name = "mm_file"
    version = "1.0.0"
    description = "Memory-mapped files: a self-contained, header-only implementation in C++ for reading and writing"
    license = "MIT"
    homepage = "https://github.com/jermp/mm_file"
    url = "https://github.com/jermp/mm_file"  # CI fills this

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # header-only: nothing to compile, only apply (empty) conandata patches
        apply_conandata_patches(self)

    def package(self):
        # Variant A: header-only library — install public headers + license
        # mm_file.hpp lives at include/mm_file/mm_file.hpp (nested), so copy
        # the whole include/ tree to preserve the include/mm_file layout.
        copy(self, "*", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()  # header-only: single package_id

    def package_info(self):
        # header-only: headers only, no libraries to link
        self.cpp_info.set_property("cmake_file_name", "mm_file")
        self.cpp_info.set_property("cmake_target_name", "mm_file::mm_file")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
