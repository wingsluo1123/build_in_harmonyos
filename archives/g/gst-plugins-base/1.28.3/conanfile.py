#!/usr/bin/env python3
"""Conan recipe — gst-plugins-base 1.28.3 (meson)

GStreamer Base Plugins — a set of essential plug-ins for GStreamer.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout
from conan.tools.gnu import PkgConfigDeps


class GstPluginsBaseConan(ConanFile):
    name = "gst-plugins-base"
    version = "1.28.3"
    description = "GStreamer Base Plugins — essential plug-ins collection"
    license = "LGPL-2.1-or-later"
    homepage = "https://gstreamer.freedesktop.org/"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gstreamer/1.28.3")
        self.requires("glib/2.84.0.1")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.project_options["iso-codes"] = "disabled"
        tc.project_options["orc"] = "disabled"
        tc.project_options["gl"] = "disabled"
        tc.project_options["examples"] = "disabled"
        tc.project_options["vorbis"] = "disabled"
        tc.project_options["theora"] = "disabled"
        tc.project_options["ogg"] = "disabled"
        tc.generate()

        pkg = PkgConfigDeps(self)
        pkg.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.compile()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib/gstreamer-1.0"]
        self.cpp_info.includedirs = ["include/gstreamer-1.0"]
        self.cpp_info.set_property("pkg_config_name", "gstreamer-plugins-base-1.0")
