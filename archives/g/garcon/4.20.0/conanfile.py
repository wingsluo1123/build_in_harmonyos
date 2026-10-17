#!/usr/bin/env python3
"""Conan recipe — garcon 4.20.0 (autotools)

garcon is the Xfce menu library (freedesktop.org menu specification
implementation, gitlab.xfce.org/xfce/garcon, LGPL-2.1+). Core libgarcon
depends on glib/gio/gobject/gthread/gtk3/libxfce4util only.

OHOS adaptation:
- Patch 0001 (Makefile.in + configure): garcon-gtk (libxfce4ui
  consumer → unpackaged xfconf chain), docs (gtk-doc) and tests
  (test-display-menu-gtk3 links the dropped garcon-gtk; all three
  test programs are noinst and NOT wired into make check) dropped
  from SUBDIRS; the core libgarcon library has no libxfce4ui dependency
  (audited: no reference outside garcon-gtk/). The pre-generated
  configure is NOT regenerated (the autotools toolchain is split
  across hnp/usr-local prefixes and the vendored XDT macros do not
  expand under local aclocal — verified empirically) — instead its
  config.status temp-dir mktemp template is redirected to the el2
  local partition: on HMFS, `umask 077 && mktemp -d ./confXXXXXX`
  yields a setgid dir the owner cannot write into (drwx--S---),
  which broke config.status's subs1.awk generation (Permission
  denied); on el2 the same sequence yields a normal drwx------ dir
  (verified empirically).
- The configure-time LIBXFCE4UI2 pkg-config probe is satisfied with a
  stub libxfce4ui-2.pc (empty flags — nothing consumes them since
  garcon-gtk is not built), written into the generators folder.
- gettext link path: the OHOS sysroot libintl is an empty stub; the
  glib package ships a proxy libintl whose g_libintl_* implementation
  lives in libglib — link -lintl through augmented .pc Libs lines
  (libxfce4util 4.20.1 precedent, merged PR #15906's recipe pattern).
- meson-style ELF codesign invalidation also applies to libtool
  installs: the packaged .so files are re-signed in package() with
  binary-sign-tool (kysdk/wlopm precedents).
- Upstream tests: tests/ ships three noinst programs (test-menu-parser,
  test-menu-spec, test-display-menu-gtk3) — they are noinst (not run
  by make check), N=0 registered test cases; consumer smoke cases in
  test_package cover library construction + parse round-trips.
"""
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class GarconConan(ConanFile):
    name = "garcon"
    version = "4.20.0"
    description = "Xfce menu library (freedesktop.org menu specification)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.xfce.org/xfce/garcon"
    url = "https://gitlab.xfce.org/xfce/garcon"
    topics = ("xfce", "menu", "freedesktop")

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

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"garcon supports Linux and OHOS only, got {self.settings.os}"
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
        # 1) OHOS pkg-config eagerly resolves Requires.private (wlrctl
        #    precedent) — glib's Requires.private: libffi would fail the
        #    plain glib-2.0 query when libffi.pc is absent. Strip libffi.
        # 2) gettext: the OHOS sysroot libintl is an empty stub; the glib
        #    package ships a proxy libintl whose g_libintl_* implementation
        #    lives in libglib — append -lintl to the glib-family Libs
        #    (libxfce4util 4.20.1 precedent).
        intl_targets = ("glib-2.0.pc", "gobject-2.0.pc", "gio-2.0.pc",
                        "gthread-2.0.pc", "gtk+-3.0.pc",
                        "libxfce4util-1.0.pc")
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

        # Stub libxfce4ui-2.pc: the untouched configure probes it with
        # pkg-config; garcon-gtk (the only consumer) is dropped from
        # SUBDIRS by patch 0001, so empty flags satisfy the probe.
        stub = os.path.join(self.generators_folder, "libxfce4ui-2.pc")
        if not os.path.isfile(stub):
            with open(stub, "w", encoding="utf-8", newline="\n") as f:
                f.write("prefix=/dummy\n"
                        "Name: libxfce4ui-2 (OHOS stub)\n"
                        "Description: stub — garcon-gtk dropped, "
                        "nothing links it\n"
                        "Version: 4.20.0\n"
                        "Libs: \nCflags: \n")

        tc = AutotoolsToolchain(self)
        # OHOS: config.guess cannot identify the HarmonyOS kernel
        # ("cannot guess build type") — pass an explicit --build triple.
        # --host is deliberately omitted: this is a native compile
        # (clang runs on the device), and the shipped config.sub does
        # not recognize "ohos" as an OS name anyway.
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
        # Drop libtool archives: the installed .la records build-machine
        # absolute paths in dependency_libs (-L/storage/Users/.../p/...)
        # and a broken '//lib' libdir, which breaks any downstream
        # libtool link resolving -lgarcon-1 through it ("not a valid
        # libtool archive" — libxfce4util 4.20.0 precedent, repo
        # history commit 2cc04f7c35; published glib/gtk ship no .la).
        rm(self, "*.la", libdir)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["garcon-1"]
        self.cpp_info.set_property("pkg_config_name", "garcon-1")
        self.cpp_info.requires = [
            "glib::glib-2.0", "glib::gio-2.0", "glib::gobject-2.0",
            "gtk::gtk+-3.0", "libxfce4util::libxfce4util-1.0",
        ]
