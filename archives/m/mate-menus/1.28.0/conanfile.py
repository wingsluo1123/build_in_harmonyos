#!/usr/bin/env python3
"""Conan recipe for mate-menus 1.28.0 — MATE desktop menu implementation library.

Build system: autotools (configure + make)
Dependencies: glib (gio-unix-2.0)
Patches: config.guess/config.sub (HarmonyOS), configure umask fix
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class MateMenusConan(ConanFile):
    name = "mate-menus"
    version = "1.28.0"
    description = "MATE desktop menu implementation library"
    license = "GPL-2.0-or-later"
    homepage = "https://mate-desktop.org"
    url = "https://pub.mate-desktop.org/releases/1.28/mate-menus-1.28.0.tar.xz"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    # glib in conan repo is shared-only, so default to shared
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.84.0.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # HarmonyOS: compiled test programs cannot be executed (security
        # restrictions), so configure thinks it's cross-compiling.
        # Pass --host explicitly to skip the "run compiled programs" check.
        if self.settings.os == "OHOS":
            tc.configure_args.append("--host=aarch64-linux-ohos")
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--enable-introspection=no")
        tc.generate()
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()

        # The glib conan recipe doesn't expose gio-unix-2.0 as a
        # PkgConfigDeps component. Set GIO_UNIX_CFLAGS and GIO_UNIX_LIBS
        # directly from the conan-managed glib package.
        glib_pkg = self.dependencies["glib"].package_folder
        if glib_pkg:
            glib_inc = os.path.join(glib_pkg, "include")
            glib_inc_glib = os.path.join(glib_pkg, "include", "glib-2.0")
            glib_inc_gio = os.path.join(glib_pkg, "include", "gio-unix-2.0")
            glib_inc_internal = os.path.join(glib_pkg, "lib", "glib-2.0", "include")
            glib_lib = os.path.join(glib_pkg, "lib")

            env = Environment()
            cflags = " ".join([
                f"-I{glib_inc_gio}",
                f"-I{glib_inc}",
                f"-I{glib_inc_glib}",
                f"-I{glib_inc_internal}",
            ])
            libs = " ".join([
                f"-L{glib_lib}",
                "-lgio-2.0",
                "-lgobject-2.0",
                "-lgmodule-2.0",
                "-lglib-2.0",
                "-lintl",
                "-lffi",
                "-lpcre2-8",
                "-lz",
                "-lm",
                "-lpthread",
                "-ldl",
            ])
            env.define("GIO_UNIX_CFLAGS", cflags)
            env.define("GIO_UNIX_LIBS", libs)
            env.vars(self).save_script("mate_menus_gio_unix")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["mate-menu"]
        self.cpp_info.includedirs = ["include/mate-menus"]
        self.cpp_info.set_property("pkg_config_name", "libmate-menu")
