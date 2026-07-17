#!/usr/bin/env python3
"""Conan recipe for wireless-regdb — regulatory database package.

wireless-regdb is a pure data package (no C/C++ compilation).
It generates regulatory database files (regulatory.bin, regulatory.db)
from db.txt using Python scripts and openssl, then installs them
to firmware/crda paths.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class WirelessRegdbConan(ConanFile):
    name = "wireless-regdb"
    version = "2026.05.30"
    description = "Linux Wireless Regulatory Database — regulatory rules for WiFi/Bluetooth"
    license = "ISC"
    homepage = "https://wireless.wiki.kernel.org/en/developers/regulatory"

    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # wireless-regdb is a data package: make generates regulatory.bin
        # and regulatory.db from db.txt using Python scripts + openssl.
        # No C/C++ compiler needed. Use -C to run from source folder.
        self.run(f"make -C {self.source_folder} -j1")

    def package(self):
        # make install uses DESTDIR to stage into package_folder.
        self.run(f"make -C {self.source_folder} install DESTDIR={self.package_folder} PREFIX=/usr")

    def package_info(self):
        # Data package: no libraries to link.
        # Expose resdirs for consumers to find regulatory database files.
        self.cpp_info.resdirs = ["lib/firmware", "usr/lib/crda"]
