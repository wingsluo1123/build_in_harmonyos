#!/usr/bin/env python3
"""Conan recipe — gnome-autoar 0.4.5 (meson)

GNOME library for creating and extracting archives.
Build system: Meson. Dependencies: glib, libarchive.
Options: gtk (disabled), introspection (disabled), tests (disabled).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout
from conan.tools.gnu import PkgConfigDeps


class GnomeAutoarConan(ConanFile):
    name = "gnome-autoar"
    version = "0.4.5"
    description = "GNOME library for creating and extracting archives"
    license = "LGPL-2.1+"
    homepage = "https://gitlab.gnome.org/GNOME/gnome-autoar"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def requirements(self):
        self.requires("glib/2.84.0.1")
        self.requires("libarchive/3.8.7")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _inject_meson_binaries(self):
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar = ce.get("ar")
        rl = ce.get("ranlib")
        if not ar:
            cc = ce.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            if bindir:
                for name in ("llvm-ar", "ar"):
                    cand = os.path.join(bindir, name)
                    if os.path.isfile(cand):
                        ar = cand
                        break
                for name in ("llvm-ranlib", "ranlib"):
                    rlc = os.path.join(bindir, name)
                    if os.path.isfile(rlc):
                        rl = rlc
                        break
        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        if not pkg_config or not os.path.isfile(str(pkg_config)):
            pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
        for nf_name in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            nf = os.path.join(self.generators_folder, nf_name)
            if not os.path.isfile(nf):
                continue
            with open(nf) as f:
                content = f.read()
            if "[binaries]" not in content:
                continue
            extras = []
            if ar and "\nar =" not in content:
                extras.append("ar = '%s'" % ar)
                if rl:
                    extras.append("ranlib = '%s'" % rl)
            if pkg_config and "\npkg-config =" not in content and "\npkgconfig =" not in content:
                extras.append("pkg-config = '%s'" % pkg_config)
            if not extras:
                continue
            content = content.replace("[binaries]\n", "[binaries]\n" + "\n".join(extras) + "\n", 1)
            with open(nf, "w") as f:
                f.write(content)

    def _fix_glib_mkenums(self):
        glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(glib_pc):
            return
        with open(glib_pc) as f:
            content = f.read()
        if "glib_mkenums" in content:
            return
        glib_dep = self.dependencies["glib"]
        mkenums = os.path.join(glib_dep.cpp_info.bindirs[0], "glib-mkenums")
        if not os.path.isfile(mkenums):
            return
        content += "\nglib_mkenums=%s\n" % mkenums
        with open(glib_pc, "w") as f:
            f.write(content)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._fix_glib_mkenums()
        tc = MesonToolchain(self)
        tc.project_options["gtk"] = "false"
        tc.project_options["introspection"] = "disabled"
        tc.project_options["tests"] = "false"
        tc.generate()
        self._inject_meson_binaries()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["gnome-autoar-0"]
        self.cpp_info.includedirs = ["include/gnome-autoar-0"]
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_target_name", "gnome-autoar::gnome-autoar")
        self.cpp_info.set_property("pkg_config_name", "gnome-autoar-0")
        self.cpp_info.requires = ["glib::glib-2.0", "glib::gobject-2.0", "glib::gio-2.0", "libarchive::libarchive"]
