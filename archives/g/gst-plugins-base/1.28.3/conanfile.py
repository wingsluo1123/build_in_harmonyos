#!/usr/bin/env python3
"""Conan recipe for gst-plugins-base 1.28.3 on OpenHarmony."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout
import os


class GstPluginsBaseConan(ConanFile):
    name = "gst-plugins-base"
    version = "1.28.3"
    description = "GStreamer base plugins and support libraries"
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
        self.requires("glib/2.84.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.project_options["introspection"] = "disabled"
        tc.project_options["tests"] = "disabled"
        tc.project_options["examples"] = "disabled"
        tc.project_options["doc"] = "disabled"
        tc.project_options["nls"] = "disabled"
        tc.project_options["iso-codes"] = "disabled"
        tc.project_options["orc"] = "disabled"
        tc.project_options["gl"] = "disabled"
        tc.project_options["vorbis"] = "disabled"
        tc.project_options["theora"] = "disabled"
        tc.project_options["ogg"] = "disabled"
        # Use system glib/pcre2/libffi .pc files (with correct prefix paths)
        home = os.path.expanduser("~")
        pkg_config_paths = [self.generators_folder]
        system_paths = [
            f"{home}/usr/local/lib/pkgconfig",
            "/data/service/hnp/pcre2.org/pcre2_10.47/lib/pkgconfig",
            "/data/service/hnp/libffi.org/libffi_3.4.4/lib/pkgconfig",
        ]
        for sp in system_paths:
            if os.path.isdir(sp):
                pkg_config_paths.append(sp)
        for dep in ["gstreamer", "glib", "pcre2", "libffi"]:
            if dep in self.dependencies:
                pkg = self.dependencies[dep].package_folder
                pkg_config_paths.append(f"{pkg}/lib/pkgconfig")
        tc.pkg_config_path = ":".join(pkg_config_paths)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = [
            "gstaudio-1.0", "gstvideo-1.0", "gstpbutils-1.0",
            "gsttag-1.0", "gstrtp-1.0", "gstrtsp-1.0",
            "gstsdp-1.0", "gstriff-1.0", "gstapp-1.0",
            "gstfft-1.0", "gstallocators-1.0",
        ]
        self.cpp_info.includedirs = ["include/gstreamer-1.0"]
