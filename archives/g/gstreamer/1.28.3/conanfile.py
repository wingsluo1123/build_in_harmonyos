#!/usr/bin/env python3
"""Conan recipe for gstreamer 1.28.3 on OpenHarmony."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class GstreamerConan(ConanFile):
    name = "gstreamer"
    version = "1.28.3"
    description = "GStreamer core library"
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
        tc.project_options["ptp-helper"] = "disabled"
        tc.project_options["bash-completion"] = "disabled"
        tc.project_options["libunwind"] = "disabled"
        tc.project_options["libdw"] = "disabled"
        tc.project_options["gst_parse"] = "false"
        # Use system glib/pcre2/libffi .pc files (with correct prefix paths) first,
        # then conan packages' .pc files as fallback
        import os
        home = os.path.expanduser("~")
        pkg_config_paths = [self.generators_folder]
        # System pkgconfig directories with correct absolute paths
        system_paths = [
            f"{home}/usr/local/lib/pkgconfig",
            "/data/service/hnp/pcre2.org/pcre2_10.47/lib/pkgconfig",
            "/data/service/hnp/libffi.org/libffi_3.4.4/lib/pkgconfig",
        ]
        for sp in system_paths:
            if os.path.isdir(sp):
                pkg_config_paths.append(sp)
        for dep in ["glib", "pcre2", "libffi"]:
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
        self.cpp_info.libs = ["gstreamer-1.0", "gstbase-1.0", "gstcontroller-1.0", "gstnet-1.0"]
        self.cpp_info.includedirs = ["include/gstreamer-1.0"]
