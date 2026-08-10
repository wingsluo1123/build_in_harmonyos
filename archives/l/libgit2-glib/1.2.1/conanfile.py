#!/usr/bin/env python3
"""Conan recipe for libgit2-glib 1.2.1 — GLib wrapper for libgit2.

Build system: Meson
Dependencies: glib/2.84.0, libgit2/1.9.0
"""
import os
from conan import ConanFile
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, save, load
from conan.tools.layout import basic_layout


class Libgit2GlibConan(ConanFile):
    name = "libgit2-glib"
    version = "1.2.1"
    description = "GLib wrapper for libgit2, providing Git repository access via GObject"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/libgit2-glib"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps"
    options = {
        "shared": [True, False],
        "introspection": [True, False],
        "python": [True, False],
        "vapi": [True, False],
        "ssh": [True, False],
    }
    default_options = {
        "shared": True,
        "introspection": False,
        "python": False,
        "vapi": False,
        "ssh": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.84.0")
        self.requires("libgit2/1.9.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["introspection"] = "false" if not self.options.introspection else "true"
        tc.project_options["python"] = "false" if not self.options.python else "true"
        tc.project_options["vapi"] = "false" if not self.options.vapi else "true"
        tc.project_options["ssh"] = "false" if not self.options.ssh else "true"
        tc.project_options["gtk_doc"] = "false"
        if not self.options.shared:
            tc.project_options["default_library"] = "static"
        tc.generate()

        # Fix: add ar/strip to meson native file (MesonToolchain doesn't set these)
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if os.path.exists(native_file):
            content = load(self, native_file)
            if "ar = " not in content:
                content = content.replace(
                    "[binaries]\n",
                    "[binaries]\nar = '/data/service/hnp/bin/llvm-ar'\nstrip = '/data/service/hnp/bin/llvm-strip'\nld = '/data/service/hnp/bin/ld.lld'\n",
                )
                save(self, native_file, content)

        # Fix: glib-2.0.pc needs glib_mkenums variable for gnome.mkenums_simple()
        glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if os.path.exists(glib_pc):
            content = load(self, glib_pc)
            if "glib_mkenums" not in content:
                # Find glib package path from dependency info
                glib_pkg = self.dependencies["glib"]
                glib_prefix = glib_pkg.package_folder
                content += f"\nglib_genmarshal={glib_prefix}/bin/glib-genmarshal\n"
                content += f"gobject_query={glib_prefix}/bin/gobject-query\n"
                content += f"glib_mkenums={glib_prefix}/bin/glib-mkenums\n"
                save(self, glib_pc, content)

        # Fix: PkgConfigDeps only generates glib-2.0.pc (single component),
        # but meson needs gobject-2.0.pc and gio-2.0.pc separately
        glib_pkg = self.dependencies["glib"]
        glib_prefix = glib_pkg.package_folder
        glib_libdir = f"{glib_prefix}/lib"
        glib_inc = f"{glib_prefix}/include/glib-2.0"
        glib_inc1 = f"{glib_prefix}/lib/glib-2.0/include"

        gobject_pc = os.path.join(self.generators_folder, "gobject-2.0.pc")
        if not os.path.exists(gobject_pc):
            save(self, gobject_pc,
                 f"prefix={glib_prefix}\n"
                 f"libdir=${{prefix}}/lib\n"
                 f"includedir=${{prefix}}/include/glib-2.0\n"
                 f"includedir1=${{prefix}}/lib/glib-2.0/include\n\n"
                 f"Name: gobject-2.0\n"
                 f"Description: GLib Type/Object Library\n"
                 f"Version: 2.84.0\n"
                 f"Requires: glib-2.0\n"
                 f"Libs: -L${{libdir}} -lgobject-2.0\n"
                 f"Cflags: -I${{includedir}} -I${{includedir1}}\n")

        gio_pc = os.path.join(self.generators_folder, "gio-2.0.pc")
        if not os.path.exists(gio_pc):
            save(self, gio_pc,
                 f"prefix={glib_prefix}\n"
                 f"libdir=${{prefix}}/lib\n"
                 f"includedir=${{prefix}}/include/glib-2.0\n"
                 f"includedir1=${{prefix}}/lib/glib-2.0/include\n\n"
                 f"Name: gio-2.0\n"
                 f"Description: GLib I/O Library\n"
                 f"Version: 2.84.0\n"
                 f"Requires: glib-2.0 gobject-2.0\n"
                 f"Libs: -L${{libdir}} -lgio-2.0\n"
                 f"Cflags: -I${{includedir}} -I${{includedir1}}\n")

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["git2-glib-1.0"]
        self.cpp_info.includedirs = ["include/libgit2-glib-1.0"]
        self.cpp_info.requires = ["glib::glib", "libgit2::libgit2"]
