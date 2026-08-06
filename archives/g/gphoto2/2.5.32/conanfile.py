#!/usr/bin/env python3
"""Conan recipe for gphoto2 2.5.32 — OHOS (OpenHarmony) aarch64 adaptation.

Build system: autotools (release tarball includes configure).
Portability patches: config.guess/config.sub for OHOS detection (E007),
main.c pthread_cancel replacement for musl/OHOS (E099).

Dependencies:
  - libgphoto2/2.5.31 (core camera access library)
  - libexif/0.6.26    (EXIF metadata support)
  - popt/1.16         (command-line option parsing)

OHOS adaptations:
  - pthread_cancel unavailable on musl/OHOS → flag-based cancellation (#ifdef __OHOS__)
  - config.guess/config.sub updated for OHOS platform detection
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class Gphoto2Conan(ConanFile):
    name = "gphoto2"
    version = "2.5.32"
    description = "Command-line utility for accessing digital cameras via libgphoto2"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/gphoto/gphoto2"
    url = ""  # CI fills this

    # CLI tool, not a library (R38: commands.json declared at software level)
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"gphoto2 is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def requirements(self):
        self.requires("libgphoto2/2.5.31")
        self.requires("libexif/0.6.26")
        self.requires("popt/1.16")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        tc.generate()
        # Ensure configure conftest programs can find shared libs at runtime
        env = Environment()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self, scope="build").save_script("conanbuild_runpath")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Standalone binary, no C++/library info
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
