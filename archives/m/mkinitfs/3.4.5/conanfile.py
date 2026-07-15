#!/usr/bin/env python3
"""Conan recipe — mkinitfs 3.4.5 (Alpine Linux initramfs generator).

Makefile project: make + make install.
Shell-script tool (no compiled C code when WITH_NLPLUG=0).
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MkinitfsConan(ConanFile):
    name = "mkinitfs"
    version = "3.4.5"
    description = "Alpine Linux initramfs generator"
    license = "GPL-2.0"
    homepage = "https://github.com/alpinelinux/mkinitfs"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: Use `in ("Linux", "OHOS")` for settings.os check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"mkinitfs supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # WITH_NLPLUG=0: skip nlplug-findfs (requires blkid, libkmod, libcryptsetup)
        # R9: Always use -j1
        # Makefile is in source_folder, run from there
        self.run(f"make -C {self.source_folder} WITH_NLPLUG=0 -j1")

    def package(self):
        # Install with DESTDIR=package_folder
        self.run(
            f'make -C {self.source_folder} install WITH_NLPLUG=0 '
            f'DESTDIR="{self.package_folder}" '
            f'sbindir=/usr/sbin sysconfdir=/etc/mkinitfs '
            f'datadir=/usr/share/mkinitfs mandir=/usr/share/man'
        )

    def package_info(self):
        self.cpp_info.bindirs = ["usr/sbin"]
        self.cpp_info.resdirs = ["etc", "usr/share"]
