#!/usr/bin/env python3
"""Conan recipe — gst-rtsp-server 1.28.3 (Meson).

GStreamer-based RTSP server library and rtspclientsink plugin.
Adapted to HarmonyOS PC (aarch64). No platform patches needed —
meson builds natively with the OHOS toolchain.

Dependencies (must be published in ohpcd conan remote):
  - gstreamer/1.28.3
  - gst-plugins-base/1.28.3
  - glib2/2.88.0
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class GstRtspServerConan(ConanFile):
    name = "gst-rtsp-server"
    version = "1.28.3"
    description = "GStreamer-based RTSP server library and rtspclientsink plugin"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.freedesktop.org/gstreamer/gst-rtsp-server"
    url = ""

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gstreamer/1.28.3")
        self.requires("gst-plugins-base/1.28.3")
        self.requires("glib2/2.88.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # CI worker exports AR/AS/STRIP/NM/RANLIB as llvm-* names that are
        # NOT on its PATH — pin the real GNU binutils by absolute path.
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {name: shutil.which(name) for name in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(
                f"Required build tools not found in PATH: {', '.join(missing)}"
            )
        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        tc.strip = tools["strip"]
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.project_options["rtspclientsink"] = "enabled"
        tc.project_options["examples"] = "disabled"
        tc.project_options["tests"] = "disabled"
        tc.project_options["introspection"] = "disabled"
        tc.project_options["doc"] = "disabled"
        tc.project_options["glib_assert"] = "false"
        tc.project_options["glib_checks"] = "false"
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
        self.cpp_info.libs = ["gstrtspserver-1.0"]
        self.cpp_info.set_property("pkg_config_name", "gstreamer-rtsp-server-1.0")
