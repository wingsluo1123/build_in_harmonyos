#!/usr/bin/env python3
"""Conan recipe for xmltoman 0.4 — Perl-based XML to man page converter.

xmltoman is a pure Perl script tool (no C/C++ compilation). The build step
applies shebang patches and installs scripts + data files via `make install`.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class XmltomanConan(ConanFile):
    name = "xmltoman"
    version = "0.4"
    description = "XML to man page conversion tool - lightweight Perl-based tool"
    license = "MIT"
    homepage = "https://sourceforge.net/projects/xmltoman/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply shebang patches (fix #!/usr/bin/perl → platform perl path)
        apply_conandata_patches(self)
        # xmltoman is pure Perl scripts — no compilation needed.
        # Install to staging directory for packaging.
        staging = os.path.join(self.build_folder, "staging")
        self.run(f"make install PREFIX=/ DESTDIR={staging}", cwd=self.source_folder)

    def package(self):
        # Copy from staging to package folder
        staging = os.path.join(self.build_folder, "staging")
        copy(self, "*", staging, self.package_folder)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
