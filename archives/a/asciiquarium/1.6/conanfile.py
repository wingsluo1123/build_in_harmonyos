#!/usr/bin/env python3
"""Conan recipe — asciiquarium 1.6

An aquarium/sea animation in ASCII art for terminal.
Pure Perl script — no compilation required, just package the script.

Build system: none (single Perl script)
License: GPL-2.0-or-later
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AsciiquariumConan(ConanFile):
    name = "asciiquarium"
    version = "1.6"
    description = "An aquarium/sea animation in ASCII art for terminal"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/nothub/asciiquarium"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # asciiquarium is a pure Perl script — no compilation needed.
        # Just ensure the script is executable.
        script = os.path.join(self.source_folder, "asciiquarium")
        if os.path.exists(script):
            os.chmod(script, 0o755)

    def package(self):
        # Install the asciiquarium script to bin/
        copy(self, "asciiquarium", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
