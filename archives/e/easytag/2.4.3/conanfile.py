#!/usr/bin/env python3
"""Conan recipe for EasyTAG 2.4.3 — Audio file metadata (tag) editor for GTK+."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class EasytagConan(ConanFile):
    name = "easytag"
    version = "2.4.3"
    description = "Audio file metadata (tag) editor for GTK+"
    license = "GPL-2.0-or-later"
    homepage = "https://wiki.gnome.org/Apps/EasyTAG"
    url = ""  # CI fills this

    # R38: easytag is a command-line/GUI application, not a library
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Core libraries (available in Conan repo)
        self.requires("glib/2.84.0.1")
        self.requires("cairo/1.18.4")
        self.requires("pango/1.56.4")
        # Audio format libraries (available in Conan repo)
        self.requires("flac/1.4.3")
        self.requires("libvorbis/1.3.7")
        self.requires("opus/1.5.2")
        # Override libogg to resolve version conflict between flac (1.3.5) and libvorbis (1.3.6)
        self.requires("libogg/1.3.6", override=True)
        # Note: gtk+-3.0, atk, gdk-pixbuf, opusfile, speex, wavpack, libid3tag, id3lib
        # are provided as system packages (cmd-pkgs) on HarmonyOS.
        # gdk-pixbuf is not declared as conan dep because its transitive dep
        # (libtiff -> libjpeg/[>=9e]) conflicts with libjpeg-turbo provider.
        # These need separate Conan adaptation for full recipe self-containment.
        # Note: gtk+-3.0, atk, opusfile, speex, wavpack, libid3tag, id3lib
        # are provided as system packages (cmd-pkgs) on HarmonyOS.
        # They need separate Conan adaptation for full recipe self-containment.

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--prefix=${prefix}")
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
        # R38: application with executables
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
