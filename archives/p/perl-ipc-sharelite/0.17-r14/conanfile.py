#!/usr/bin/env python3
"""Conan recipe — IPC::ShareLite Perl XS module (Makefile.PL + make).

Build system: Perl ExtUtils::MakeMaker (Makefile.PL)
This is a Perl XS module with C extension code (sharestuff.c + ShareLite.xs).
Provides lightweight SysV shared memory segments for Perl.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlipcshareliteConan(ConanFile):
    name = "perl-ipc-sharelite"
    version = "0.17-r14"
    description = "IPC::ShareLite — lightweight SysV shared memory for Perl"
    license = "Artistic-1.0-Perl OR GPL-1.0-or-later"
    homepage = "https://metacpan.org/dist/IPC-ShareLite"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No Conan dependencies — uses system Perl (ExtUtils::MakeMaker)
        pass

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Perl XS module build: Makefile.PL generates Makefile, then make compiles C/XS code
        self.run("perl Makefile.PL", cwd=self.source_folder)
        self.run("make", cwd=self.source_folder)

    def package(self):
        # Copy built artifacts to package folder in standard layout
        # .so goes to lib/auto/IPC/ShareLite/ (Perl auto path)
        # .pm goes to lib/IPC/ (Perl module path)
        src = self.source_folder
        blib_arch = os.path.join(src, "blib", "arch")
        blib_lib = os.path.join(src, "blib", "lib")

        copy(self, "ShareLite.so",
             src=os.path.join(blib_arch, "auto", "IPC", "ShareLite"),
             dst=os.path.join(self.package_folder, "lib", "auto", "IPC", "ShareLite"))
        copy(self, "*.bs",
             src=os.path.join(blib_arch, "auto", "IPC", "ShareLite"),
             dst=os.path.join(self.package_folder, "lib", "auto", "IPC", "ShareLite"))
        copy(self, "ShareLite.pm",
             src=os.path.join(blib_lib, "IPC"),
             dst=os.path.join(self.package_folder, "lib", "IPC"))
        copy(self, "autosplit.ix",
             src=os.path.join(blib_lib, "auto", "IPC", "ShareLite"),
             dst=os.path.join(self.package_folder, "lib", "auto", "IPC", "ShareLite"))

    def package_info(self):
        # The shared library is ShareLite.so (Perl XS extension)
        self.cpp_info.libs = ["ShareLite"]
        self.cpp_info.libdirs = ["lib/auto/IPC/ShareLite"]
        # Perl module path for consumers
        self.cpp_info.includedirs = []
