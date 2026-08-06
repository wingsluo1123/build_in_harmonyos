#!/usr/bin/env python3
"""Conan recipe — gst-plugins-good 1.28.3 (meson)

GStreamer Good Plugins — a set of well-maintained plug-ins for GStreamer.
This recipe builds the "good" plugin set with platform-appropriate options
for HarmonyOS (OHOS) aarch64.

Dependencies:
  - gstreamer/1.28.3 (core GStreamer library)
  - gst-plugins-base/1.28.3 (base GStreamer plugins)
  - glib/2.84.0.1 (GLib core library)
  - cairo/1.18.4 (2D graphics library)
  - flac/1.4.3 (FLAC audio codec)
  - libjpeg-turbo/3.2.0 (JPEG codec)
  - libpng/1.6.58 (PNG codec)

Disabled plugins (platform limitations on OHOS):
  - v4l2: V4L2 kernel headers not available
  - oss/oss4: OSS audio subsystem not available
  - pulse: PulseAudio not available
  - jack: JACK audio not available
  - dv1394: IEEE 1394 not available
  - soup: libsoup not available
  - gtk3/gdk-pixbuf: GTK3 runtime not available
  - qt5/qt6: Qt not available
  - ximagesrc: X11 not available
  - orc: ORC compiler not available
  - directsound/osxaudio/osxvideo/waveform: Other-platform specific
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout
from conan.tools.gnu import PkgConfigDeps


class GstPluginsGoodConan(ConanFile):
    name = "gst-plugins-good"
    version = "1.28.3"
    description = "GStreamer Good Plugins — well-maintained plug-ins collection"
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
        self.requires("gst-plugins-base/1.28.3")
        self.requires("glib/2.84.0.1")
        self.requires("cairo/1.18.4")
        self.requires("flac/1.4.3")
        self.requires("libjpeg-turbo/3.2.0")
        self.requires("libpng/1.6.58")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # R26: Non-system libraries default to shared (Conan manages deps)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"

        # Disable platform-incompatible plugins (OHOS/HarmonyOS)
        tc.project_options["v4l2"] = "disabled"
        tc.project_options["oss"] = "disabled"
        tc.project_options["oss4"] = "disabled"
        tc.project_options["ximagesrc"] = "disabled"
        tc.project_options["jack"] = "disabled"
        tc.project_options["pulse"] = "disabled"
        tc.project_options["dv1394"] = "disabled"
        tc.project_options["soup"] = "disabled"
        tc.project_options["gtk3"] = "disabled"
        tc.project_options["gdk-pixbuf"] = "disabled"
        tc.project_options["qt5"] = "disabled"
        tc.project_options["qt6"] = "disabled"
        tc.project_options["directsound"] = "disabled"
        tc.project_options["osxaudio"] = "disabled"
        tc.project_options["osxvideo"] = "disabled"
        tc.project_options["waveform"] = "disabled"
        tc.project_options["examples"] = "disabled"
        tc.project_options["tests"] = "disabled"
        tc.project_options["doc"] = "disabled"
        tc.project_options["glib_assert"] = "false"
        tc.project_options["glib_checks"] = "false"
        tc.project_options["orc"] = "disabled"

        tc.generate()

        # Generate pkg-config files for dependencies
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
        # GStreamer plugins are installed to lib/gstreamer-1.0/
        # They are loaded dynamically by the GStreamer registry
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib/gstreamer-1.0"]
        self.cpp_info.includedirs = ["include/gstreamer-1.0"]
        self.cpp_info.resdirs = ["lib/gstreamer-1.0"]
