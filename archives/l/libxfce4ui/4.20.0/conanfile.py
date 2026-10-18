#!/usr/bin/env python3
"""Conan recipe — libxfce4ui 4.20.0 (autotools)

libxfce4ui is the Xfce widget library (dialogs, spawn, filename input,
titled dialog; gitlab.xfce.org/xfce/libxfce4ui, LGPL-2.1+). Core
libxfce4ui-2 depends on glib/gtk3/libxfce4util only.

OHOS adaptation (patch 0001 — pre-generated artifacts only):
- Makefile.in (top): libxfce4kbd-private (X shortcut helper),
  xfce4-about (needs kbd-private), glade (glade plugin), docs
  (gtk-doc) and tests (link the dropped pieces) removed from SUBDIRS.
- libxfce4ui/Makefile.in: xfce-screensaver.{c,h} removed — the ONLY
  file referencing xfconf (audited: 16 references in one file, no
  other core file touches it; xfconf is not packaged for OHOS and
  pulls its own dependency chain). The screensaver API is a
  documented public-API removal.
- configure: the XFCONF and GDK_WAYLAND pkg-config probes stubbed to
  succeed-with-empty-flags (the gtk package is a broadway-only build
  with no wayland backend — wayland code paths are
  GDK_WINDOWING_WAYLAND-guarded and compile out; the stub only
  satisfies configure's "one of X11/Wayland must be enabled" gate);
  the config.status temp-dir mktemp template redirected to the el2
  local partition — on HMFS,
  'umask 077 && mktemp -d ./confXXXXXX' yields a setgid dir the
  owner cannot write into, breaking config.status (Permission
  denied; el2 unaffected — garcon 4.20.0 precedent).
- gettext link path: -lintl appended to glib-family .pc Libs
  (libxfce4util 4.20.1 precedent — the g_libintl_* implementation
  lives in libglib's private libintl).
- Packaged .so files re-signed in package() with binary-sign-tool
  (OHOS rejects unsigned ELFs; kysdk/wlopm/garcon precedents).
- Upstream tests: tests/ programs link the dropped subdirs — N=0
  registered; consumer smoke covers version macros + GType
  registration round-trip.
"""
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class Libxfce4uiConan(ConanFile):
    name = "libxfce4ui"
    version = "4.20.0"
    description = "Xfce widget library (dialogs, spawn, titled dialog)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.xfce.org/xfce/libxfce4ui"
    url = "https://gitlab.xfce.org/xfce/libxfce4ui"
    topics = ("xfce", "widget", "gtk")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("glib/2.84.0.1")
        self.requires("gtk/3.24.43")
        self.requires("libxfce4util/4.20.1")

    def build_requirements(self):
        # libxfce4ui's configure REQUIRES at least one of X11/Wayland to be
        # enabled ("Either both X11 and Wayland support was disabled...
        # One of the two must be enabled"). X11 is not packaged for OHOS;
        # the wayland package (build context only — satisfied through the
        # stub gdk-wayland-3.0.pc, actual wayland code paths are
        # GDK_WINDOWING_WAYLAND-guarded and compile out, so the library
        # links nothing from it) provides the gate evidence.
        # wlopm 1.0.0 tool_requires precedent (libxml2 for the scanner).
        self.tool_requires("wayland/1.22.0")
        # Graph conflict resolution: wayland/1.22.0 pins expat/2.8.2 while
        # the gtk chain pulls expat/2.8.2.1 — override to the newer one
        # (gtk 3.24.43.1 recipe uses the same override pattern for
        # cairo/glib version unification).
        self.requires("expat/2.8.2.1", override=True)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libxfce4ui supports Linux and OHOS only, got {self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # PkgConfigDeps first: emits .pc files into the generators folder
        # and the conanbuild env points PKG_CONFIG_PATH there.
        PkgConfigDeps(self).generate()

        # Post-process the generated .pc files in place:
        # 1) Strip libffi from Requires.private (OHOS pkg-config eagerly
        #    resolves it — wlrctl precedent).
        # 2) Append -lintl to glib-family Libs (libxfce4util 4.20.1
        #    precedent — the OHOS sysroot libintl is an empty stub).
        intl_targets = ("glib-2.0.pc", "gobject-2.0.pc", "gio-2.0.pc",
                        "gtk+-3.0.pc", "libxfce4util-1.0.pc")
        for name in os.listdir(self.generators_folder):
            if not name.endswith(".pc"):
                continue
            path = os.path.join(self.generators_folder, name)
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            content = re.sub(
                r"(?m)^(Requires\.private:.*)$",
                lambda m: re.sub(r"\blibffi[^ ]*", "", m.group(1)).strip(),
                content)
            content = re.sub(r"(?m)^(Requires\.private:\s*)$",
                             "# OHOS: stripped empty Requires.private",
                             content)
            if name in intl_targets and "-lintl" not in content:
                content = re.sub(r"(?m)^(Libs:.*)$", r"\1 -lintl", content)
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)

        # Stub gdk-wayland-3.0.pc: configure's optional-feature gate
        # REQUIRES one of X11/Wayland to pass the pkg-config --exists /
        # --atleast-version / --modversion checks (three layers). The gtk
        # package is a broadway-only build with no wayland backend, so a
        # stub .pc satisfies every layer at once (garcon's
        # libxfce4ui-2.pc stub precedent); actual wayland code paths are
        # GDK_WINDOWING_WAYLAND-guarded in the gtk headers (undefined in
        # a broadway build) and compile out.
        stub_wl = os.path.join(self.generators_folder, "gdk-wayland-3.0.pc")
        if not os.path.isfile(stub_wl):
            with open(stub_wl, "w", encoding="utf-8", newline="\n") as f:
                f.write("prefix=/dummy\n"
                        "Name: gdk-wayland-3.0 (OHOS stub)\n"
                        "Description: stub — broadway-only gtk, wayland "
                        "paths compile out\n"
                        "Version: 3.24.0\n"
                        "Libs: \nCflags: \n")

        tc = AutotoolsToolchain(self)
        # OHOS: config.guess cannot identify the HarmonyOS kernel — pass
        # an explicit --build triple; --host omitted (native compile, the
        # shipped config.sub does not recognize "ohos" as an OS name).
        tc.configure_args.append("--build=aarch64-linux")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    @staticmethod
    def _sign_elf(path):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise ConanInvalidConfiguration("binary-sign-tool not found")
        tmp = path + ".signed"
        subprocess.run([signer, "sign", "-inFile", path, "-outFile", tmp,
                        "-selfSign", "1"], check=True, timeout=60)
        os.chmod(tmp, 0o755)
        os.replace(tmp, path)

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            for name in os.listdir(libdir):
                if name.endswith(".so") and os.path.isfile(os.path.join(libdir, name)):
                    self._sign_elf(os.path.join(libdir, name))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["xfce4ui-2"]
        self.cpp_info.set_property("pkg_config_name", "libxfce4ui-2")
        self.cpp_info.requires = [
            "glib::glib-2.0", "glib::gobject-2.0", "glib::gio-2.0",
            "gtk::gtk+-3.0", "libxfce4util::libxfce4util-1.0",
        ]
