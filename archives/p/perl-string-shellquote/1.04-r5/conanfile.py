#!/usr/bin/env python3
"""Conan recipe for perl-string-shellquote 1.04-r5 (pure Perl module).

This module provides String::ShellQuote for quoting strings for shell use.
Build system: Perl ExtUtils::MakeMaker (perl Makefile.PL && make && make install).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlStringShellQuoteConan(ConanFile):
    name = "perl-string-shellquote"
    version = "1.04-r5"
    description = "String::ShellQuote - quote strings for passing through the shell"
    license = "Perl"  # Same terms as Perl itself
    homepage = "https://metacpan.org/dist/String-ShellQuote"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure Perl module: use ExtUtils::MakeMaker
        self.run("perl Makefile.PL", cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Install using DESTDIR to stage into package_folder
        destdir = self.package_folder
        self.run(f'make install DESTDIR="{destdir}"', cwd=self.source_folder)

    def package_info(self):
        # Pure Perl module: no C libraries to link
        # Set include dirs and lib dirs for consumers
        self.cpp_info.libs = []
