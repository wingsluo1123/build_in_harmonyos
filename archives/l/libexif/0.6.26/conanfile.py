#!/usr/bin/env python3
"""Conan recipe for libexif 0.6.26 — OHOS (OpenHarmony) aarch64 adaptation.

Build system: autotools (configure + make).
Portability patches: config.guess/config.sub for OHOS detection (E007),
configure temp-dir fix for HMDFS/SELinux (E097).
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibexifConan(ConanFile):
    name = "libexif"
    version = "0.6.26"
    description = "Library for parsing, editing, and saving EXIF data"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/libexif/libexif"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libexif is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["exif"]
