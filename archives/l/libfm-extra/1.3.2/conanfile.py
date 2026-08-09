#!/usr/bin/env python3
"""Conan recipe — libfm-extra 1.3.2 (Autotools).

libfm-extra is the XML file processing library from the LXDE libfm project.
It provides fm_xml_file_* API for parsing and manipulating XML files,
independent of GTK. Built with --with-extra-only to exclude GTK dependencies.

Adapted to HarmonyOS PC (aarch64). See notes.md for platform adaptations.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class LibfmExtraConan(ConanFile):
    name = "libfm-extra"
    version = "1.3.2"
    description = "XML file processing library from LXDE libfm (extra-only, no GTK)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/lxde/libfm"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib2/2.88.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--with-extra-only")
        tc.configure_args.append("--disable-nls")
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

        # Generate .pc files for direct dependencies (glib2 → pcre2, zlib)
        pkg = PkgConfigDeps(self)
        pkg.generate()

        # glib2's package ships .pc files for gio-unix-2.0, gthread-2.0,
        # gobject-2.0 that PkgConfigDeps doesn't generate (no set_property
        # for those sub-components). Add the package's pkgconfig dir to
        # PKG_CONFIG_PATH so configure can find them.
        env = Environment()
        for dep_name, dep in self.dependencies.items():
            pkgconfig_dir = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if os.path.isdir(pkgconfig_dir):
                env.append_path("PKG_CONFIG_PATH", pkgconfig_dir)
        env.vars(self).save_script("conan_dep_pkgconfig")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["fm-extra"]
        self.cpp_info.includedirs = ["include/libfm-1.0"]
        self.cpp_info.set_property("cmake_target_name", "libfm-extra::libfm-extra")
        self.cpp_info.set_property("pkg_config_name", "libfm-extra")
