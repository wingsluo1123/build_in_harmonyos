#!/usr/bin/env python3
"""Conan recipe for perl-sereal (Sereal) 5.004-r1

Sereal is a fast, compact, powerful binary (de-)serialization format for Perl.
This is the front-end module that wraps Sereal::Encoder and Sereal::Decoder.

Build system: Perl ExtUtils::MakeMaker (Makefile.PL)
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlSerealConan(ConanFile):
    name = "perl-sereal"
    version = "5.004-r1"
    description = "Fast, compact, powerful binary (de-)serialization for Perl (front-end module)"
    license = "MIT"
    homepage = "https://github.com/Sereal/Sereal"
    url = ""  # CI fills this

    # R32: settings.os must check in ("Linux", "OHOS")
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R27: dependencies must use @ohpcd/stable
        self.requires("perl-sereal-encoder/5.004@ohpcd/stable")
        self.requires("perl-sereal-decoder/5.004-r3@ohpcd/stable")

    def validate(self):
        # R32: settings.os judgment must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}. Only Linux and OHOS are supported."
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Perl module build: Makefile.PL + make
        # Use ExtUtils::MakeMaker instead of Module::Build
        # Run in source folder since basic_layout separates source/build dirs
        self.run("perl Makefile.PL", cwd=self.source_folder)
        self.run("make", cwd=self.source_folder)

    def package(self):
        # Copy the built Perl module from blib/lib to package lib/
        # blib/lib/Sereal.pm is the output of make
        copy(self, "*.pm",
             src=os.path.join(self.source_folder, "blib", "lib"),
             dst=os.path.join(self.package_folder, "lib"),
             keep_path=False)

    def package_info(self):
        # R26: This is a pure Perl module, no C/C++ libraries
        self.cpp_info.libs = []

        # Set up PERL5LIB path for consumers
        perl5lib = os.path.join(self.package_folder, "lib")
        self.runenv_info.append_path("PERL5LIB", perl5lib)
        # Also set build env for consumers
        self.buildenv_info.append_path("PERL5LIB", perl5lib)
