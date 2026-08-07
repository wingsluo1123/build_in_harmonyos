#!/usr/bin/env python3
"""Conan recipe — pavucontrol 6.2 (meson)

PulseAudio Volume Control — a simple GTK4-based volume control tool for
the PulseAudio sound server. This is a C++ application using gtkmm-4.0.

Dependencies (required by meson.build):
  - gtkmm-4.0 >= 4.0      [NOT in conan repo yet — needs building]
  - sigc++-3.0            [available as libsigc]
  - libpulse >= 5.0       [NOT in conan repo yet — needs building]
  - libpulse-mainloop-glib [NOT in conan repo — part of libpulse]
  - json-glib-1.0         [conditional — NOT in conan repo]
  - libcanberra >= 0.16   [optional — audio-feedback feature]
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain, meson_layout


class PavucontrolConan(ConanFile):
    name = "pavucontrol"
    version = "6.2"
    description = "PulseAudio Volume Control — GTK4-based volume control for PulseAudio"
    license = "GPL-2.0-or-later"
    homepage = "https://www.freedesktop.org/software/pulseaudio/pavucontrol/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gtkmm-4.0/4.16.0")  # GTK4 C++ bindings (not yet in repo)
        self.requires("libsigc/3.6.0")     # provides sigc++-3.0
        self.requires("libpulse/17.0")     # PulseAudio client library (not yet in repo)
        self.requires("json-glib/1.10.8")  # JSON GLib (conditional dep, not yet in repo)

    def layout(self):
        meson_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # pavucontrol is an application — use shared libs
        tc.project_options["default_library"] = "shared"
        # Disable optional features not available on OHOS
        tc.project_options["audio-feedback"] = "disabled"
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
        # pavucontrol is a command-line/GUI application
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
