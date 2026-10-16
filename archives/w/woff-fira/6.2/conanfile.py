#!/usr/bin/env python3
"""Conan recipe for the Fira Code 6.2 WOFF webfont data package."""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


FONT_FILES = {
    "FiraCode-Bold.woff",
    "FiraCode-Light.woff",
    "FiraCode-Medium.woff",
    "FiraCode-Regular.woff",
    "FiraCode-SemiBold.woff",
    "FiraCode-VF.woff",
}


class WoffFiraConan(ConanFile):
    name = "woff-fira"
    version = "6.2"
    description = "Fira Code 6.2 WOFF webfont resources"
    license = "OFL-1.1"
    homepage = "https://github.com/tonsky/FiraCode"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "unknown"
    settings = "os", "compiler", "build_type", "arch"

    _font_subdir = os.path.join("share", "fonts", "woff-fira", "woff")

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "LICENSE", self.recipe_folder, self.export_sources_folder)

    def layout(self):
        basic_layout(self)

    def source(self):
        # The release archive has several top-level directories, including woff/.
        get(self, **self.conan_data["sources"], strip_root=False)
        apply_conandata_patches(self)

    def build(self):
        font_dir = os.path.join(self.source_folder, "woff")
        if not os.path.isdir(font_dir):
            raise ConanException(f"Upstream WOFF directory not found: {font_dir}")

        actual_files = {name for name in os.listdir(font_dir) if name.endswith(".woff")}
        if actual_files != FONT_FILES:
            raise ConanException(
                f"Expected exactly {len(FONT_FILES)} WOFF files; found {sorted(actual_files)}"
            )

        for name in sorted(FONT_FILES):
            path = os.path.join(font_dir, name)
            with open(path, "rb") as font_file:
                header = font_file.read(44)
            if len(header) != 44 or header[:4] != b"wOFF":
                raise ConanException(f"Invalid WOFF header: {name}")
            declared_length = int.from_bytes(header[8:12], "big")
            table_count = int.from_bytes(header[12:14], "big")
            reserved = int.from_bytes(header[14:16], "big")
            if declared_length != os.path.getsize(path) or table_count == 0 or reserved != 0:
                raise ConanException(f"Inconsistent WOFF header: {name}")

    def package(self):
        source_font_dir = os.path.join(self.source_folder, "woff")
        destination = os.path.join(self.package_folder, self._font_subdir)
        copy(self, "*.woff", source_font_dir, destination, keep_path=False)
        copy(
            self,
            "LICENSE",
            self.export_sources_folder,
            os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.resdirs = [self._font_subdir]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []
