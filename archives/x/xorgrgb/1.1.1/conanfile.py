#!/usr/bin/env python3
"""Conan recipe — xorgrgb 1.1.1 (Autotools)

X.org RGB color database tool providing the `showrgb` command
and the X11 color name → RGB mapping data file (rgb.txt).
"""
import os

from conan import ConanFile
from conan.tools.files import get, save, load, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class XorgrgbConan(ConanFile):
    name = "xorgrgb"
    version = "1.1.1"
    description = "X.org RGB color database tool (showrgb + rgb.txt)"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/app/rgb"
    url = "https://gitlab.freedesktop.org/xorg/app/rgb"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # System build dependencies (installed via cmd-pkgs, not in conan remote):
    #   xorgproto/2024.1  — X11 protocol header files
    #   util-macros/1.20.2 — X.Org autotools m4 macros

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Set prefix so showrgb can find rgb.txt at {prefix}/share/X11/rgb.txt
        tc.configure_args.append(f"--prefix={self.package_folder}")
        tc.configure_args.append("--with-rgb-db-type=text")
        tc.generate()

    def build(self):
        # Expose system-installed X11 dependencies (xorgproto, util-macros)
        # These are build-time include/m4 paths, not compiler flags (R33 safe)
        prefix = os.path.expanduser("~/usr/local")
        pkgconfig_lib = os.path.join(prefix, "lib", "pkgconfig")
        pkgconfig_share = os.path.join(prefix, "share", "pkgconfig")
        aclocal = os.path.join(prefix, "share", "aclocal")
        includes = os.path.join(prefix, "include")

        cur_pc = os.environ.get("PKG_CONFIG_PATH", "")
        new_pc = f"{pkgconfig_lib}:{pkgconfig_share}"
        os.environ["PKG_CONFIG_PATH"] = f"{new_pc}:{cur_pc}" if cur_pc else new_pc

        cur_ac = os.environ.get("ACLOCAL_PATH", "")
        os.environ["ACLOCAL_PATH"] = f"{aclocal}:{cur_ac}" if cur_ac else aclocal

        cur_inc = os.environ.get("C_INCLUDE_PATH", "")
        os.environ["C_INCLUDE_PATH"] = f"{includes}:{cur_inc}" if cur_inc else includes

        # E011: HMDFS umask 077 causes config.status temp dir unwritable.
        # Fix: replace umask 077 → umask 022 in configure after autoreconf.
        # (R6: configure is a generated file, so fix at build time, not via patch.)
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.autoreconf(args=["-fi"])

        # E165: Fix shebang paths for OpenHarmony (/bin/sh → /system/bin/sh)
        configure_path = os.path.join(self.source_folder, "configure")
        configure_content = load(self, configure_path)
        configure_content = configure_content.replace("umask 077", "umask 022")
        configure_content = configure_content.replace("#! /bin/sh", "#! /system/bin/sh")
        configure_content = configure_content.replace("#!/bin/sh", "#! /system/bin/sh")
        save(self, configure_path, configure_content)

        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        # --prefix={package_folder} set in generate(), so make install
        # installs directly to the package folder (no DESTDIR needed)
        autotools.make(args=["install"])

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
