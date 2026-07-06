import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.layout import basic_layout


class BcryptConan(ConanFile):
    name = "bcrypt"
    version = "1.0"
    description = "bcrypt password hashing library with Blowfish encryption and auto-salting"
    license = "BSD"
    homepage = "https://github.com/rg3/libbcrypt"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Fix Makefiles: use clang instead of gcc, remove x86 assembly (not available on aarch64)
        mk = os.path.join(self.source_folder, "Makefile")
        replace_in_file(self, mk, "CC = gcc", "CC = clang")

        cb_mk = os.path.join(self.source_folder, "crypt_blowfish", "Makefile")
        replace_in_file(self, cb_mk, "CC = gcc", "CC = clang")
        # Remove x86.o from BLOWFISH_OBJS (x86 assembly not available on aarch64)
        replace_in_file(self, cb_mk, "crypt_blowfish.o x86.o", "crypt_blowfish.o")

        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        copy(self, "bcrypt.h", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "bcrypt.a", self.source_folder, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["bcrypt"]
