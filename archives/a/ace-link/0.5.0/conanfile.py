#!/usr/bin/env python3
"""Conan recipe for ace-link — GNU Emacs package for selecting a link to jump to.

ace-link is a pure Emacs Lisp package. No C/C++ compilation needed.
Build() copies .el files to the package directory.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AceLinkConan(ConanFile):
    name = "ace-link"
    version = "0.5.0"
    description = "GNU Emacs package for selecting a link to jump to"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/abo-abo/ace-link"
    url = ""  # CI fills this

    package_type = "library"

    # R32: os removed from settings — ace-link is pure Emacs Lisp, OS-independent
    settings = "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # emacs and avy are runtime dependencies loaded by Emacs at runtime,
        # not Conan build-time dependencies. They are documented in notes.md.
        # When emacs itself is ported to OHOS, these can be added as proper requires.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["source"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # ace-link is pure Emacs Lisp — no C/C++ compilation.
        # Just copy .el files. The Makefile only does byte-compilation,
        # which requires Emacs runtime, not a cross-compilation toolchain.
        # R32: os removed from settings — pure Emacs Lisp is OS-independent,
        # no platform restrictions needed.
        pass

    def package(self):
        # Copy .el files to the package lib directory (site-lisp for Emacs)
        copy(self, "*.el", self.source_folder, os.path.join(self.package_folder, "lib", "site-lisp"))
        # Copy README and LICENSE if present
        copy(self, "README*", self.source_folder, os.path.join(self.package_folder, "lib", "site-lisp"))
        copy(self, "LICENSE*", self.source_folder, os.path.join(self.package_folder, "lib", "site-lisp"))

    def package_info(self):
        # Emacs Lisp packages don't have C/C++ libraries to link against.
        # The .el files are loaded by Emacs at runtime.
        self.cpp_info.includedirs = ["lib/site-lisp"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
