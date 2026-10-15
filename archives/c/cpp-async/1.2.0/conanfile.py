#!/usr/bin/env python3
"""Conan recipe for cpp-async 1.2.0 — Header-only C++ coroutine library.

cpp-async provides header-only awaitable/task abstractions under include/async/.
No build step; package() redistributes headers. Patches fix two upstream
clang/C++20 compatibility issues (see patches/ and notes.md):
  0001: non-member operator co_await overload resolution under C++20 concepts
  0002-0008: remove invalid `constexpr` from test helpers whose await_suspend
             body calls assert(false) (ill-formed constexpr in C++20).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, copy, export_conandata_patches
from conan.tools.layout import basic_layout


class CppasyncConan(ConanFile):
    name = "cpp-async"
    version = "1.2.0"
    description = "Libraries for non-blocking concurrent programming using C++11 coroutines (header-only)"
    license = "MIT"
    homepage = "https://github.com/microsoft/cpp-async"
    url = ""  # CI fills this

    package_type = "header-library"   # header-only: no shared option required

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    # Header-only: no build step; leave build() empty (G1 structural check)
    def build(self):
        pass

    def package(self):
        # 源码树: include/async/*.h → 包内 include/async/（copy 保留相对路径）
        copy(self, "include/async/*.h", src=self.source_folder,
             dst=self.package_folder)
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()          # header-only: single package_id

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []