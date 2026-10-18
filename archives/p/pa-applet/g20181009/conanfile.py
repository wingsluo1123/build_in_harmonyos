#!/usr/bin/env python3
"""Conan recipe for pa-applet g20181009 on HarmonyOS PC (aarch64).

pa-applet is a PulseAudio control applet for the GTK+ system tray: it shows a
tray icon and raises/lowers/mutes the default sink, with optional global
media-key grabbing and desktop notifications.

Version note: g20181009 is the FreeBSD ports naming (PORTVERSION g20181009);
it pins the upstream commit fernandotcl/pa-applet@3b4f8b3 — upstream has no
tag with that name.

OHOS-specific adaptations:
  - Upstream is autotools-only (configure.ac + Makefile.am + autogen.sh) and
    the git snapshot ships no generated configure. The build environment has
    no automake/aclocal/libtool, so autogen.sh dies with
    "Error: aclocal is required to run ./autogen.sh". This recipe therefore
    carries its own CMakeLists.txt reproducing the upstream Makefile.am
    source set and install rules (same approach as pamixer/1.6 and the other
    recipes in this archive that ship a CMakeLists.txt).
  - src/key_grabber.c unconditionally includes <gdk/gdkx.h> and uses
    GDK_DISPLAY_XDISPLAY / XGrabKey for the global media keys. The published
    gtk/3.24.43 is a broadway-only build (gdkconfig.h carries
    "#undef GDK_WINDOWING_X11" and gdk/gdkx.h is not installed), so that
    translation unit cannot compile as-is. patches/0001 guards the X11-only
    code with the toolkit's own backend macro GDK_WINDOWING_X11 and keeps the
    public key_grabber API (emitting a diagnostic) when the backend is
    absent — no platform macro is introduced. Reuses the knowledge entry
    DRAFT-gui-toolkit-backend-macro-guard.
  - Dependency-line convergence: gtk/3.24.43 sits on glib/2.84.0.1 +
    zlib/1.3.1.1 + gdk-pixbuf/2.44.6.1, while libnotify/0.8.3.1 pulls the
    glib/2.88 line. Rebuilding gtk is prohibitive, so glib/zlib/gdk-pixbuf
    are forced onto gtk's line and only libnotify is rebuilt from source (a
    small meson library). expat is pinned to 2.8.2.1 as in paprefs/1.2.
    pulseaudio/17.0 (not 17.0.1) is used because 17.0.1 requires
    glib/2.88.0 and would force a glib-line change.
  - Runtime limits: the OHOS PC session provides no system-tray host and no
    org.freedesktop.Notifications daemon, and global hotkeys additionally
    need the X11 GDK backend. The binary builds, links and starts, but tray
    icon, notifications and hotkeys are inert. See notes.md.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class PaAppletConan(ConanFile):
    name = "pa-applet"
    version = "g20181009"
    description = "PulseAudio GTK+ volume control applet for the system tray"
    homepage = "https://github.com/fernandotcl/pa-applet"
    license = "GPL-3.0-or-later"
    topics = ("pulseaudio", "gtk", "applet", "system-tray", "audio")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "CMakeLists.txt", "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gtk/3.24.43")
        # 17.0.1 才带 libpulse-mainloop-glib 组件（pa-applet 用 pa_glib_mainloop
        # 把 libpulse 回调接进 GTK 主循环）；17.0 的配方没有 glib 组件。
        self.requires("pulseaudio/17.0.1")
        self.requires("libnotify/0.8.3.1")
        # 守住 gtk/3.24.43 的依赖线（glib 2.84 / zlib 1.3.1.1 /
        # gdk-pixbuf 2.44.6.1），只让 libnotify 走源码重建，避免重编 gtk。
        self.requires("glib/2.84.0.1", force=True)
        self.requires("zlib/1.3.1.1", force=True)
        self.requires("gdk-pixbuf/2.44.6.1", force=True)
        # paprefs/1.2 已验证的 expat 收敛点。
        self.requires("expat/2.8.2.1", override=True)
        # pango 的 pango-coverage.h 直接 include <hb.h>，但其 CMake 目标没有把
        # harfbuzz 的 include 目录传播给消费者；显式声明（版本与图中一致）补齐。
        self.requires("harfbuzz/14.2.0.1.1.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # conan 在 source() 之后把源树复制到构建目录，补丁必须在此打，
        # 放到 build() 里只会改 s/、编译的却是 b/src 副本。
        apply_conandata_patches(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
