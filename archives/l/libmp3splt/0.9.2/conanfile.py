#!/usr/bin/env python3
"""Conan recipe for libmp3splt 0.9.2 — library for mp3/ogg/flac splitting."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibMp3SpltConan(ConanFile):
    name = "libmp3splt"
    version = "0.9.2"
    description = "Library for mp3/ogg/flac splitting without decoding"
    license = "GPL-2.0+"
    homepage = "https://mp3splt.sourceforge.net"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libmad/0.15.1b")
        self.requires("libid3tag/0.16.3")
        self.requires("libogg/1.3.5")
        self.requires("libvorbis/1.3.7")
        self.requires("flac/1.4.3")
        self.requires("pcre2/10.45")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
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
        self.cpp_info.libs = ["mp3splt"]
        self.cpp_info.set_property("pkg_config_name", "libmp3splt")
