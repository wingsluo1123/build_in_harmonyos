#!/usr/bin/env python3
"""Conan recipe for audacious-plugins 4.5.1 — Audacious audio player plugins.

Provides input/output codecs, effects, containers, and transport plugins.
Built with autotools (configure + make).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AudaciousPluginsConan(ConanFile):
    name = "audacious-plugins"
    version = "4.5.1"
    description = "Plugins for the Audacious audio player (codecs, effects, outputs, transports)"
    license = "BSD-2-Clause"
    homepage = "https://audacious-media-player.org/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Conan repo (ohpcd) dependencies
        self.requires("glib/2.84.0.1")
        self.requires("flac/1.4.3")
        self.requires("libxml2/2.15.3.1")
        self.requires("opus/1.5.2.1")
        self.requires("opusfile/0.12")
        self.requires("ffmpeg/8.1.2")
        self.requires("zlib/1.3.2")
        # Non-conan dependencies (installed via cmd-pkgs or system)
        # audacious, mpg123, libvorbis, alsa-lib, wavpack, neon, openssl,
        # pcre2, libffi, libogg

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--prefix=${PACKAGE_FOLDER}")
        # GTK and Qt UI plugins disabled: gtk+-3.0 and Qt6Svg not available
        # in conan repo. All codec/transport/output plugins remain enabled.
        tc.configure_args.append("--disable-gtk")
        tc.configure_args.append("--disable-qt")
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
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = ["lib/audacious"]
