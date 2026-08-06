#!/usr/bin/env python3
"""Conan recipe for libsoup 2.74.3 on HarmonyOS PC (arm64).

Build system: meson
Dependencies: glib, libpsl, libxml2, sqlite3, brotli

The old historical adaptation stubbed out gnome.compile_resources() because
the HNP system's glib-compile-resources was broken (missing libffi.so.8).
With Conan-managed glib, the working glib-compile-resources from the Conan
glib package is used, so no stub patch is needed.
"""

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps


class LibsoupConan(ConanFile):
    name = "libsoup"
    version = "2.74.3"
    description = "HTTP client/server library for GNOME"
    license = "LGPL-2.0-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/libsoup"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.84.0")
        self.requires("libpsl/0.21.5")
        self.requires("libxml2/2.15.3")
        self.requires("sqlite3/3.49.1")
        self.requires("brotli/1.2.0")

    def layout(self):
        self.folders.source = "src"
        self.folders.build = "build"
        self.folders.generators = "build"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # Disable TLS check: glib-networking not available at compile time
        tc.project_options["tls_check"] = "false"
        # Disable sysprof: not needed on OHOS
        tc.project_options["sysprof"] = "disabled"
        # Disable tests: separate test_package handles testing
        tc.project_options["tests"] = "false"
        # Disable GNOME-specific features (po subdirectory)
        tc.project_options["gnome"] = "false"
        # Disable GObject introspection
        tc.project_options["introspection"] = "disabled"
        # Disable Vala bindings
        tc.project_options["vapi"] = "disabled"
        # Disable GTK doc generation
        tc.project_options["gtk_doc"] = "false"
        tc.generate()
        pkg = PkgConfigDeps(self)
        pkg.generate()

    def build(self):
        import os
        # Fix: meson auto-detects llvm-ar as archiver for clang but can't find it
        os.environ["AR"] = "/data/service/hnp/bin/llvm-ar"
        os.environ["RANLIB"] = "/data/service/hnp/bin/llvm-ranlib"
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.compile()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["soup-2.4"]
        self.cpp_info.set_property("pkg_config_name", "libsoup-2.4")
        # Public transitive dependencies
        self.cpp_info.requires = ["glib", "libpsl", "libxml2"]
