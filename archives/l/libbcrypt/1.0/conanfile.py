#!/usr/bin/env python3
"""Conan recipe for libbcrypt — simple Makefile project.

libbcrypt is a bcrypt password hashing C library wrapping the crypt_blowfish
implementation from Solar Designer (OpenWall). It builds a static library
(bcrypt.a) and provides the bcrypt.h header.

Build system: raw Makefile (no configure, no CMake).
Patches:
  - CC ?= gcc (allow compiler override from Conan toolchain)
  - Remove x86 assembly (x86.o) for ARM64 compatibility
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibbcryptConan(ConanFile):
    name = "libbcrypt"
    version = "1.0"
    description = "Blowfish-based bcrypt password hashing library"
    license = "CC0-1.0"
    homepage = "https://github.com/rg3/libbcrypt"
    url = "https://github.com/rg3/libbcrypt"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Use AutotoolsToolchain to set CC, CXX, CFLAGS etc. from Conan profile
        # The Makefile's "CC ?= gcc" will pick up CC from this environment
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # R26: Only build static library, no shared variant
        # CC comes from AutotoolsToolchain environment (no hardcoded compiler)
        # libbcrypt uses in-source build (no out-of-source support)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        copy(self, "bcrypt.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        copy(self, "bcrypt.a", src=self.source_folder, dst=os.path.join(self.package_folder, "lib"))
        # Rename to libbcrypt.a for standard find_library convention
        src_path = os.path.join(self.package_folder, "lib", "bcrypt.a")
        dst_path = os.path.join(self.package_folder, "lib", "libbcrypt.a")
        if os.path.exists(src_path):
            shutil.move(src_path, dst_path)

    def package_info(self):
        self.cpp_info.libs = ["bcrypt"]
