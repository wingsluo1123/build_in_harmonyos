#!/usr/bin/env python3
"""Conan recipe for xfce4-pulseaudio-plugin 0.5.1 — Xfce panel PulseAudio plugin.

This plugin is a GModule (.so) loaded at runtime by xfce4-panel.
Build system: autotools (configure + make).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Xfce4PulseaudiopluginConan(ConanFile):
    name = "xfce4-pulseaudio-plugin"
    version = "0.5.1"
    description = "Pulseaudio plugin for the Xfce panel"
    license = "GPL-2.0-only"
    homepage = "https://gitlab.xfce.org/panel-plugins/xfce4-pulseaudio-plugin"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libxfce4util/4.19.6")
        self.requires("xfconf/4.19.4")
        self.requires("libxfce4ui/4.19.6")
        self.requires("exo/4.19.4")
        self.requires("garcon/4.19.4")
        self.requires("libxfce4panel/4.19.6")
        self.requires("libpulse/17.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Disable optional features unavailable on OHOS
        tc.configure_args.append("--disable-keybinder")
        tc.configure_args.append("--disable-libnotify")
        tc.configure_args.append("--disable-libcanberra")
        tc.configure_args.append("--disable-libxfce4windowing")
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
        self.cpp_info.libs = ["pulseaudio-plugin"]
        self.cpp_info.libdirs = ["lib/xfce4/panel/plugins"]
