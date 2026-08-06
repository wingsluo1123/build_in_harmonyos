#!/usr/bin/env python3
"""Conan recipe for mp3splt-gtk 0.9.2 — GTK GUI for mp3splt.

mp3splt-gtk is a GTK3-based GUI for splitting MP3/OGG/FLAC files
without decoding, using libmp3splt as the backend library.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Mp3SpltGtkConan(ConanFile):
    name = "mp3splt-gtk"
    version = "0.9.2"
    description = "GTK GUI for mp3splt — split MP3/OGG files without decoding"
    license = "GPL-2.0"
    homepage = "https://mp3splt.sourceforge.net"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libmp3splt/0.9.2")
        self.requires("gtk/3.24.51")
        self.requires("glib/2.84.0.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-audacious")
        tc.configure_args.append("--disable-gstreamer")
        tc.configure_args.append("--disable-gnome")
        tc.configure_args.append("--disable-doxygen_doc")
        tc.configure_args.append("--disable-cutter")
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
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
