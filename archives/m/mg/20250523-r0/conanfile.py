#!/usr/bin/env python3
"""Conan recipe for mg (microscopic EMACS style editor) 20250523-r0.

mg is a portable version of the OpenBSD maintained mg editor.
It uses a GNUmakefile with pkg-config to find ncurses and libbsd.

System dependencies (pre-installed in CI environment):
  - ncurses/6.4 (dev headers + pkg-config)
  - libbsd/0.12.2 (dev headers + pkg-config)
  - libmd/1.1.0 (dev headers + pkg-config)
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MgConan(ConanFile):
    name = "mg"
    version = "20250523-r0"
    description = "microscopic EMACS style editor"
    license = "Public-Domain"
    homepage = "https://github.com/hboetes/mg"
    url = "https://github.com/hboetes/mg"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # mg uses GNUmakefile directly with pkg-config for dependencies
        # CC, CFLAGS, CPPFLAGS, LDFLAGS come from the CI environment
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Install mg binary
        self.run(f"install -d {self.package_folder}/bin")
        self.run(f"install -m 755 mg {self.package_folder}/bin/", cwd=self.source_folder)
        # Install man page
        self.run(f"install -d {self.package_folder}/man/man1")
        self.run(f"install -m 644 mg.1 {self.package_folder}/man/man1/", cwd=self.source_folder)

    def package_info(self):
        # mg is a command-line tool, not a library
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []