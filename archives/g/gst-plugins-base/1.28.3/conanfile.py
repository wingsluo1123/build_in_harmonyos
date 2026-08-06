#!/usr/bin/env python3
"""Conan recipe for gst-plugins-base 1.28.3 on OpenHarmony."""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


class GstPluginsBaseConan(ConanFile):
    name = "gst-plugins-base"
    version = "1.28.3"
    description = "GStreamer base plugins and support libraries"
    license = "LGPL-2.1-or-later"
    homepage = "https://gstreamer.freedesktop.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

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
        # Build pkg-config search path from conan deps + system paths
        pkg_config_paths = [self.generators_folder]
        # System pkgconfig dirs (OHOS dev environment) with fallback paths
        sys_pc = os.environ.get("PKG_CONFIG_PATH", "")
        system_paths = sys_pc.split(":") if sys_pc else []
        # Fallback: common OHOS system pkgconfig locations
        fallback_paths = [
            os.path.expanduser("~/usr/local/lib/pkgconfig"),
            "/data/service/hnp/pcre2.org/pcre2_10.47/lib/pkgconfig",
            "/data/service/hnp/libffi.org/libffi_3.4.4/lib/pkgconfig",
        ]
        for fp in fallback_paths:
            if fp not in system_paths and os.path.isdir(fp):
                system_paths.append(fp)
        for sp in system_paths:
            if sp and os.path.isdir(sp):
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
