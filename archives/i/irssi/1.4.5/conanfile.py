#!/usr/bin/env python3
"""Conan recipe for irssi 1.4.5 — terminal IRC client (Meson build).

irssi is a terminal-based IRC client built with Meson.
Dependencies: glib, openssl, ncurses (all from Conan registry).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout
from conan.tools.gnu import PkgConfigDeps


class IrssiConan(ConanFile):
    name = "irssi"
    version = "1.4.5"
    description = "irssi is a terminal-based IRC client"
    license = "GPL-2.0-or-later"
    homepage = "https://irssi.org"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.84.0")
        self.requires("openssl/3.5.6")
        self.requires("ncurses/6.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Set archiver paths for meson (llvm-ar not in default PATH in CI)
        os.environ.setdefault("AR", "/data/service/hnp/bin/llvm-ar")
        os.environ.setdefault("RANLIB", "/data/service/hnp/bin/llvm-ranlib")
        # Generate pkg-config files for dependencies (glib, openssl, ncurses)
        pc = PkgConfigDeps(self)
        pc.generate()
        # glib conan recipe bundles gmodule into glib-2.0 component.
        # Generate a gmodule-2.0.pc alias so meson can find it.
        glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        gmodule_pc = os.path.join(self.generators_folder, "gmodule-2.0.pc")
        if os.path.exists(glib_pc) and not os.path.exists(gmodule_pc):
            with open(glib_pc, "r") as f:
                glib_content = f.read()
            gmodule_content = glib_content.replace("glib-2.0", "gmodule-2.0", 1)
            with open(gmodule_pc, "w") as f:
                f.write(gmodule_content)
        tc = MesonToolchain(self)
        # R26: System-name libraries default to static
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # Disable Perl (not available on HarmonyOS)
        tc.project_options["with-perl"] = "no"
        # Request static dependency linking
        tc.project_options["static-dependency"] = "yes"
        # Enable true color support
        tc.project_options["enable-true-color"] = "yes"
        # Add ncurses lib path for cc.find_library() (meson doesn't use pkg-config for terminfo)
        ncurses = self.dependencies.get("ncurses")
        if ncurses:
            for libdir in ncurses.cpp_info.libdirs:
                tc.c_link_args.append(f"-L{libdir}")
                tc.cpp_link_args.append(f"-L{libdir}")
        tc.generate()
        # Patch the generated meson native file to add ar/ranlib binaries
        # (OHOS conan 2.29.1 MesonToolchain doesn't emit ar in [binaries])
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if os.path.exists(native_file):
            with open(native_file, "r") as f:
                content = f.read()
            if "[binaries]" in content and "ar =" not in content:
                content = content.replace(
                    "[binaries]\n",
                    "[binaries]\nar = '/data/service/hnp/bin/llvm-ar'\nranlib = '/data/service/hnp/bin/llvm-ranlib'\n"
                )
                with open(native_file, "w") as f:
                    f.write(content)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["irssi"]
        self.cpp_info.bindirs = ["bin"]
