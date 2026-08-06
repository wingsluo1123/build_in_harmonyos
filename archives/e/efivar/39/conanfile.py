#!/usr/bin/env python3
"""Conan recipe for efivar 39 — EFI variable management library.

Build system: plain Makefile (not autotools/cmake).
Patches: musl libc compatibility shims (qsort_r, secure_getenv,
         program_invocation_short_name).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class EfivarConan(ConanFile):
    name = "efivar"
    version = "39"
    description = "Tools and libraries to work with EFI variables"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/rhboot/efivar"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: Try to get compiler from Conan conf, fall back to platform defaults
        try:
            cc = self.conf.get("tools.build:compiler_executables:c") or "clang"
        except Exception:
            cc = "clang"
        try:
            ar = self.conf.get("tools.build:compiler_executables:ar") or "llvm-ar"
        except Exception:
            ar = "llvm-ar"
        try:
            ranlib = self.conf.get("tools.build:compiler_executables:ranlib") or "llvm-ranlib"
        except Exception:
            ranlib = "llvm-ranlib"
        # R9: Use -j1
        self.run(f"make CC={cc} CCLD={cc} AR={ar} RANLIB={ranlib} ENABLE_DOCS=0 -j1", cwd=self.source_folder)

    def package(self):
        # Install using make install with conan-friendly paths
        pkg = self.package_folder
        self.run(
            f"make install DESTDIR= "
            f"LIBDIR={pkg}/lib "
            f"INCLUDEDIR={pkg}/include/efivar "
            f"BINDIR={pkg}/bin "
            f"PCDIR={pkg}/lib/pkgconfig "
            f"ENABLE_DOCS=0",
            cwd=self.source_folder
        )
        # Also copy the public headers from src/include/efivar/ (make install
        # copies from include/ but some headers are only in src/)
        copy(self, "*.h",
             os.path.join(self.source_folder, "src/include/efivar"),
             os.path.join(pkg, "include/efivar"))

    def package_info(self):
        self.cpp_info.libs = ["efivar", "efiboot", "efisec"]
        self.cpp_info.includedirs = ["include/efivar"]
        self.cpp_info.bindirs = ["bin"]
