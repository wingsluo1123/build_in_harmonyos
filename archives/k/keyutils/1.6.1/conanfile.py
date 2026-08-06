#!/usr/bin/env python3
"""Conan recipe for keyutils 1.6.1 — Linux key management library.

Build system: plain Makefile.
Patches: musl libc compatibility (rindex -> strrchr, index -> strchr).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class KeyutilsConan(ConanFile):
    name = "keyutils"
    version = "1.6.1"
    description = "Linux key management utilities and library"
    license = "GPL-2.0-or-later"
    homepage = "https://git.kernel.org/pub/scm/linux/kernel/git/dhowells/keyutils.git"
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
        self.run(f"make CC={cc} CFLAGS='-g -Wall -fPIC -O2' AR={ar} RANLIB={ranlib} -j1", cwd=self.source_folder)

    def package(self):
        pkg = self.package_folder
        src = self.source_folder
        # Copy library files manually (avoid broken symlinks from make install)
        copy(self, "libkeyutils.so*", src, os.path.join(pkg, "lib"), keep_path=False)
        copy(self, "libkeyutils.a", src, os.path.join(pkg, "lib"), keep_path=False)
        # Copy header
        copy(self, "keyutils.h", src, os.path.join(pkg, "include"), keep_path=False)
        # Copy binaries
        copy(self, "keyctl", src, os.path.join(pkg, "bin"), keep_path=False)
        # Fix symlinks: create proper dev symlink
        libdir = os.path.join(pkg, "lib")
        if os.path.lexists(os.path.join(libdir, "libkeyutils.so.1.9")):
            os.makedirs(libdir, exist_ok=True)
            # Remove broken symlinks first
            for s in ["libkeyutils.so", "libkeyutils.so.1"]:
                p = os.path.join(libdir, s)
                if os.path.islink(p):
                    os.unlink(p)
            # Create proper relative symlinks
            os.symlink("libkeyutils.so.1.9", os.path.join(libdir, "libkeyutils.so.1"))
            os.symlink("libkeyutils.so.1", os.path.join(libdir, "libkeyutils.so"))

    def package_info(self):
        self.cpp_info.libs = ["keyutils"]
        self.cpp_info.bindirs = ["bin"]
