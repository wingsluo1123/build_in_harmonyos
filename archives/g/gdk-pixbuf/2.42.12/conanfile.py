#!/usr/bin/env python3
"""Conan recipe for gdk-pixbuf 2.42.12 (Meson build system)."""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, collect_libs
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class GdkpixbufConan(ConanFile):
    name = "gdk-pixbuf"
    version = "2.42.12"
    description = "GTK+ image loading library"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/gdk-pixbuf"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.84.0")
        self.requires("libpng/1.6.58")
        self.requires("libjpeg-turbo/3.2.0")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        # Post-process glib-2.0.pc: add Requires for pcre2 and libffi (static linking)
        _pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if os.path.isfile(_pc):
            with open(_pc) as f:
                _c = f.read()
            if "Requires:" not in _c:
                _c = _c.replace("Version:", "Requires: pcre2 libffi\nVersion:", 1)
                with open(_pc, "w") as f:
                    f.write(_c)
        tc = MesonToolchain(self)
        tc.project_options["gio_sniffing"] = "false"
        tc.project_options["tiff"] = "disabled"
        tc.project_options["tests"] = "false"
        tc.project_options["man"] = "false"
        tc.project_options["default_library"] = "shared"
        tc.generate()
        # Inject ar/ranlib full path into conan_meson_native.ini
        _ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        _ar = _ce.get("ar")
        _rl = _ce.get("ranlib")
        if not _ar:
            _cc = _ce.get("c") or ""
            _bindir = os.path.dirname(_cc) if os.path.sep in _cc else ""
            if _bindir:
                _cand = os.path.join(_bindir, "llvm-ar")
                if os.path.isfile(_cand):
                    _ar = _cand
                    _rlc = os.path.join(_bindir, "llvm-ranlib")
                    if os.path.isfile(_rlc):
                        _rl = _rlc
        _nf = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if _ar and os.path.isfile(_nf):
            with open(_nf) as _f:
                _c = _f.read()
            if "\nar =" not in _c and "[binaries]" in _c:
                _ins = "[binaries]\nar = '%s'\n" % _ar
                if _rl:
                    _ins += "ranlib = '%s'\n" % _rl
                _c = _c.replace("[binaries]\n", _ins, 1)
                with open(_nf, "w") as _f:
                    _f.write(_c)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()

    def package_info(self):
        self.cpp_info.libs = collect_libs(self)
        self.cpp_info.includedirs = ["include/gdk-pixbuf-2.0"]
        self.cpp_info.set_property("pkg_config_name", "gdk-pixbuf-2.0")
