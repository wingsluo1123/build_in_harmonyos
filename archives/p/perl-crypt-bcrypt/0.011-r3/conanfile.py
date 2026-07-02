#!/usr/bin/env python3
"""Conan recipe — Crypt::Bcrypt (Perl XS module).

Crypt::Bcrypt is a modern bcrypt implementation for Perl.
It uses ExtUtils::MakeMaker (Makefile.PL) and includes a C XS extension
(Bcrypt.xs → Bcrypt.c) plus the crypt_blowfish C library.

Build: perl Makefile.PL → make → make install
"""
import os
import glob
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlCryptBcryptConan(ConanFile):
    name = "perl-crypt-bcrypt"
    version = "0.011-r3"
    description = "A modern bcrypt implementation for Perl (XS module)"
    license = "Artistic-1.0-Perl OR GPL-1.0-or-later"
    homepage = "https://github.com/Leont/crypt-bcrypt"
    url = ""  # CI fills this

    # XS module compiles C code — needs compiler/build_type
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply patches if any
        apply_conandata_patches(self)
        # Perl XS module: use Makefile.PL (ExtUtils::MakeMaker)
        self.run("perl Makefile.PL", cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Install to a temporary DESTDIR
        dest_dir = os.path.join(self.build_folder, "destdir")
        self.run("make install DESTDIR={}".format(dest_dir), cwd=self.source_folder)

        # Find and copy the compiled .so (XS shared library)
        so_files = glob.glob(os.path.join(dest_dir, "**", "auto", "Crypt", "Bcrypt", "Bcrypt.so"), recursive=True)
        if so_files:
            target_dir = os.path.join(self.package_folder, "lib", "perl5", "auto", "Crypt", "Bcrypt")
            os.makedirs(target_dir, exist_ok=True)
            shutil.copy2(so_files[0], target_dir)

        # Find and copy the .pm (Perl module file)
        pm_files = glob.glob(os.path.join(dest_dir, "**", "Crypt", "Bcrypt.pm"), recursive=True)
        if pm_files:
            target_dir = os.path.join(self.package_folder, "lib", "perl5", "Crypt")
            os.makedirs(target_dir, exist_ok=True)
            shutil.copy2(pm_files[0], target_dir)

        # Copy the C header for direct C usage
        header_src = os.path.join(self.source_folder, "crypt_blowfish.h")
        if os.path.exists(header_src):
            inc_dir = os.path.join(self.package_folder, "include")
            os.makedirs(inc_dir, exist_ok=True)
            shutil.copy2(header_src, inc_dir)

    def package_info(self):
        # XS module produces Bcrypt.so for Perl DynaLoader
        self.cpp_info.libs = ["Bcrypt"]
        # Set PERL5LIB to the package's perl lib directory
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.runenv_info.append_path("PERL5LIB", perl_lib)
        self.buildenv_info.append_path("PERL5LIB", perl_lib)
