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
        # Override PERL5LIB to prioritize HNP module paths over HMDFS,
        # avoiding dlopen restriction on XS shared libraries (Cwd.so, etc.)
        os.environ["PERL5LIB"] = (
            "/data/service/hnp/perl.org/perl_5.42.0/lib/5.42.0/aarch64-linux:"
            "/data/service/hnp/perl.org/perl_5.42.0/lib/5.42.0:"
            "/storage/Users/currentUser/usr/local/lib/perl5"
        )
        # Add OHOS SDK sysroot paths for system headers (sys/types.h, etc.)
        sysroot = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr"
        llvm_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos"
        os.environ["C_INCLUDE_PATH"] = (
            sysroot + "/include:" + sysroot + "/include/aarch64-linux-ohos:"
            + os.environ.get("C_INCLUDE_PATH", "")
        )
        os.environ["LIBRARY_PATH"] = (
            sysroot + "/lib/aarch64-linux-ohos:" + llvm_lib + ":"
            + os.environ.get("LIBRARY_PATH", "")
        )
        # Perl XS module: use Makefile.PL (ExtUtils::MakeMaker)
        self.run("perl Makefile.PL", cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)
        # Create static library from pure C object (no Perl XS dependencies)
        self.run("ar rcs libcrypt_blowfish.a crypt_blowfish.o", cwd=self.source_folder)

    def package(self):
        # Install to a temporary DESTDIR
        dest_dir = os.path.join(self.build_folder, "destdir")
        self.run("make install DESTDIR={}".format(dest_dir), cwd=self.source_folder)

        # Find and copy the compiled .so (XS shared library)
        so_files = glob.glob(os.path.join(dest_dir, "**", "auto", "Crypt", "Bcrypt", "Bcrypt.so"), recursive=True)
        if so_files:
            # Copy to Perl autoload path for Perl DynaLoader
            perl_target = os.path.join(self.package_folder, "lib", "perl5", "auto", "Crypt", "Bcrypt")
            os.makedirs(perl_target, exist_ok=True)
            shutil.copy2(so_files[0], perl_target)

        # Copy static C library for C consumers (pure C, no Perl XS deps)
        static_lib = os.path.join(self.source_folder, "libcrypt_blowfish.a")
        if os.path.exists(static_lib):
            lib_dir = os.path.join(self.package_folder, "lib")
            os.makedirs(lib_dir, exist_ok=True)
            shutil.copy2(static_lib, lib_dir)

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
        # C library interface (crypt_blowfish functions in libcrypt_blowfish.a)
        self.cpp_info.set_property("cmake_file_name", "CryptBcrypt")
        self.cpp_info.set_property("cmake_target_name", "CryptBcrypt::CryptBcrypt")
        self.cpp_info.libs = ["crypt_blowfish"]
        self.cpp_info.libdirs = ["lib"]
        # Set PERL5LIB to the package's perl lib directory
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.runenv_info.append_path("PERL5LIB", perl_lib)
        self.buildenv_info.append_path("PERL5LIB", perl_lib)
