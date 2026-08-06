#!/usr/bin/env python3
"""Conan recipe for libgphoto2 2.5.31 — OHOS (OpenHarmony) aarch64 adaptation.

Build system: autotools (GitHub archive → autoreconf → configure → make).
Portability patches: config.guess/config.sub for OHOS detection (E007),
auto-m4/pkg.m4 added for PKG_CHECK_MODULES macro support.

Dependencies:
  - libtool/2.5.4  (provides ltdl library + libtoolize + m4 macros)
  - libexif/0.6.26 (EXIF metadata library)
  - popt/1.16      (command-line option parsing)
  - zlib/1.3.1     (compression)

OHOS adaptations:
  - USB IOLib disabled (--without-libusb1) due to OpenHarmony USB API differences
  - NLS disabled (--disable-nls) to avoid gettext build complexity
  - autoreconf needs explicit m4 directory includes (auto-m4, gphoto-m4)
"""
import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class Libgphoto2Conan(ConanFile):
    name = "libgphoto2"
    version = "2.5.31"
    description = "Core library for accessing digital cameras"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/gphoto/libgphoto2"
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
                f"libgphoto2 is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def requirements(self):
        self.requires("libtool/2.5.4")
        self.requires("libexif/0.6.26")
        self.requires("popt/1.16")
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-nls")
        tc.configure_args.append("--without-libusb1")
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()
        # Ensure autoreconf finds project-local m4 directories
        env = Environment()
        src = self.source_folder
        for m4dir in ["auto-m4", "gphoto-m4", "libgphoto2_port/gphoto-m4"]:
            path = os.path.join(src, m4dir)
            if os.path.isdir(path):
                env.append_path("ACLOCAL_PATH", path)
        env.vars(self, scope="build").save_script("conanbuild_aclocal")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # GitHub archive tarball doesn't include configure; autoreconf first
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.output.info("Source tree has no configure (GitHub archive), running autoreconf")
            autotools.autoreconf()
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["gphoto2", "gphoto2_port"]
        self.cpp_info.requires = ["gphoto2_port"]
        # Provide subpackage for gphoto2_port
        self.cpp_info.components["gphoto2_port"].libs = ["gphoto2_port"]
