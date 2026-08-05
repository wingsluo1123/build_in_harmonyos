#!/usr/bin/env python3
"""Conan recipe for asciiquarium 1.6 — a pure Perl script.

asciiquarium is an aquarium/sea animation in ASCII art for terminal.
It is a single Perl script (no C/C++ compilation needed). The "build"
step is simply verifying the script is present and valid.

Runtime dependencies (Perl modules, not conan packages):
  - Perl >= 5.42.0
  - Term::Animation >= 2.0
  - Curses (Perl module)

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

    settings = "os", "compiler", "build_type", "arch"

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
        # Pure Perl script — no compilation step
        # Verify the script exists and is a valid Perl script
        script = os.path.join(self.source_folder, "asciiquarium")
        if not os.path.isfile(script):
            raise Exception("asciiquarium script not found in source")
        with open(script, "r") as f:
            first_line = f.readline().strip()
            if "perl" not in first_line:
                raise Exception("asciiquarium is not a valid Perl script (shebang mismatch)")

    def package(self):
        # Install the Perl script to bin/
        copy(self, "asciiquarium", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        # Install documentation
        copy(self, "LICENSE.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "doc"))
        copy(self, "README.md", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "doc"))
        copy(self, "CHANGES.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "doc"))

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
