#!/usr/bin/env python3
"""Conan recipe for grilo-plugins 0.3.16 — GNOME Grilo media source plugins.

Build system: Meson
Plugins enabled: chromaprint, dleyna, gravatar, local-metadata, lua-factory,
                 magnatune, metadata-store, opensubtitles, raitv, shoutcast, tmdb
Plugins auto-disabled (missing deps): bookmarks, dmap, filesystem, flickr, freebox,
                 optical-media, podcasts, thetvdb, tracker, tracker3, youtube
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain, meson_layout


class GriloPluginsConan(ConanFile):
    name = "grilo-plugins"
    version = "0.3.16"
    description = "GNOME Grilo framework media source plugins"
    license = "LGPL-2.1-or-later"
    homepage = "https://gnome.pages.gitlab.gnome.org/grilo/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Conan-available dependencies
        self.requires("glib2/2.88.0")
        self.requires("libxml2/2.15.3")
        self.requires("sqlite3/3.49.1")
        self.requires("lua/5.4.8")

    def layout(self):
        meson_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["help"] = "no"
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
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
        # Plugin shared libraries installed to lib/grilo-0.3/
        self.cpp_info.libs = [
            "grlchromaprint",
            "grldleyna",
            "grlgravatar",
            "grllocalmetadata",
            "grlluafactory",
            "grlmagnatune",
            "grlmetadatastore",
            "grlopensubtitles",
            "grlraitv",
            "grlshoutcast",
            "grltmdb",
        ]
        self.cpp_info.libdirs = ["lib", "lib/grilo-0.3"]
