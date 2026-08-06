#!/usr/bin/env python3
"""Conan recipe for mokutil 0.7.2 — Machine Owner Key utility.

Build system: custom (autotools source, but automake unavailable on OHOS,
so we compile directly with the compiler).

Dependencies: openssl, efivar, keyutils.
Patches: musl libc compatibility (musl_shim.c/h, remove -fshort-wchar,
         replace shadow.h).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MokutilConan(ConanFile):
    name = "mokutil"
    version = "0.7.2"
    description = "Utility to manipulate Machine Owner Keys (MOK) for UEFI Secure Boot"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/lcp/mokutil"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6")
        self.requires("efivar/39")
        self.requires("keyutils/1.6.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Get compiler (R33: from conan conf where available)
        try:
            cc = self.conf.get("tools.build:compiler_executables:c") or "clang"
        except Exception:
            cc = "clang"

        src = os.path.join(self.source_folder, "src")

        # Collect include dirs and lib dirs from dependencies
        inc_dirs = []
        lib_dirs = []
        libs = []
        for dep in ["openssl", "efivar", "keyutils"]:
            if dep in self.dependencies:
                info = self.dependencies[dep].cpp_info
                inc_dirs.extend(info.includedirs)
                lib_dirs.extend(info.libdirs)
                libs.extend(info.libs)

        cflags = " ".join(f"-I{d}" for d in inc_dirs)
        cflags += " -std=gnu11 '-DVERSION=\"0.7.2\"' -fPIC -O2"

        # Source files (including musl_shim.c from patches)
        sources = [
            "mokutil.c", "efi_hash.c", "efi_x509.c",
            "keyring.c", "password-crypt.c", "util.c",
            "musl_shim.c"
        ]

        # Compile each source file
        obj_files = []
        for s in sources:
            obj = s.replace(".c", ".o")
            self.run(f"{cc} {cflags} -c {os.path.join(src, s)} -o {obj}", cwd=self.build_folder)
            obj_files.append(obj)

        # Link
        ldflags = " ".join(f"-L{d}" for d in lib_dirs)
        lib_flags = " ".join(f"-l{l}" for l in libs)
        lib_flags += " -lcrypt -ldl"
        objs = " ".join(obj_files)
        self.run(f"{cc} {ldflags} {objs} -o mokutil {lib_flags}", cwd=self.build_folder)

    def package(self):
        # Copy the binary
        copy(self, "mokutil", self.build_folder, os.path.join(self.package_folder, "bin"))
        # Copy man page if available
        man_src = os.path.join(self.source_folder, "man")
        if os.path.isdir(man_src):
            copy(self, "mokutil.1", man_src, os.path.join(self.package_folder, "share/man/man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
