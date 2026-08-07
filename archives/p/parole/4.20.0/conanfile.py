#!/usr/bin/env python3
"""Conan recipe for parole — XFCE media player based on GStreamer.

parole is a media player for the XFCE desktop environment, built with meson.
It depends on GTK3, GStreamer, D-Bus, and XFCE libraries.

Build: meson + ninja
License: GPL-2.0-or-later
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain


class ParoleConan(ConanFile):
    name = "parole"
    version = "4.20.0"
    description = "Modern media player based on GStreamer for the XFCE desktop environment"
    license = "GPL-2.0-or-later"
    homepage = "https://docs.xfce.org/apps/parole/start"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Core dependencies (required by meson.build)
        self.requires("glib/2.84.0.1")
        self.requires("gtk/3.24.38")
        self.requires("dbus/1.14.10")
        self.requires("dbus-glib/0.112")
        self.requires("gstreamer/1.28.3")
        # XFCE desktop environment libraries
        self.requires("libxfce4util/4.20.0")
        self.requires("xfconf/4.20.0")
        self.requires("libxfce4ui/4.20.0")

    def layout(self):
        self.folders.build = "build"
        self.folders.source = "."
        self.cpp.build.libdir = "lib"
        self.cpp.build.bindir = "bin"
        self.cpp.package.libdir = "lib"
        self.cpp.package.bindir = "bin"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # Disable optional features whose dependencies are unavailable
        tc.project_options["taglib"] = "disabled"
        tc.project_options["notify-plugin"] = "disabled"
        # X11 backend (Wayland not available on OHOS)
        tc.project_options["x11"] = "enabled"
        tc.project_options["wayland"] = "disabled"
        # Disable gtk-doc
        tc.project_options["gtk-doc"] = "false"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.compile()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        # parole is an application — declare bindirs for executables
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
