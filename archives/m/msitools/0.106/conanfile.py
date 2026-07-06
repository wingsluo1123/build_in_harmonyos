#!/usr/bin/env python3
"""Conan recipe — msitools 0.106 (Meson build).

Requires: glib, libgsf, libxml2 (from conan @ohpcd/stable)
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps


class MsitoolsConan(ConanFile):
    name = "msitools"
    version = "0.106"
    description = "A set of programs to inspect and build Windows Installer (.MSI) files"
    license = "LGPL-2.1-or-later"
    homepage = "https://wiki.gnome.org/msitools"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.84.0@ohpcd/stable")
        self.requires("libgsf/1.14.58@ohpcd/stable")
        self.requires("libxml2/2.15.3@ohpcd/stable")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        mb_path = os.path.join(self.source_folder, "meson.build")
        lmb_path = os.path.join(self.source_folder, "libmsi", "meson.build")
        if os.path.exists(mb_path):
            with open(mb_path) as f:
                content = f.read()
            # (1) Remove 'vala' from project() languages (valac not available)
            content = content.replace("'c', 'vala',", "'c',")
            # (2) Conan generates libgsf.pc, not libgsf-1.pc
            content = content.replace(
                "libgsf = dependency('libgsf-1')",
                "libgsf = dependency('libgsf')"
            )
            # (3) Official tarball makes libgcab unconditional, but it's not in
            #     conan cache. Restore the introspection guard around libgcab.
            old_gcab = "libgcab = dependency('libgcab-1.0', version: '>= 0.1.10')"
            new_gcab = (
                "if get_option('introspection')\n"
                "  libgcab = dependency('libgcab-1.0', version: '>= 0.1.10')\n"
                "endif"
            )
            content = content.replace(old_gcab, new_gcab)
            with open(mb_path, "w") as f:
                f.write(content)
        # (4) Official tarball uses shared_library; switch to static_library (R26)
        if os.path.exists(lmb_path):
            with open(lmb_path) as f:
                lcontent = f.read()
            # shared_library → static_library and drop version arg (not supported)
            lcontent = lcontent.replace(
                "libmsi = shared_library('msi-1.0',",
                "libmsi = static_library('msi-1.0',"
            )
            lcontent = lcontent.replace("  version: '0.0.0',\n", "")
            with open(lmb_path, "w") as f:
                f.write(lcontent)

    def generate(self):
        deps = PkgConfigDeps(self)
        deps.generate()
        tc = MesonToolchain(self)
        # R26: Static linking for the library to avoid system path pollution
        tc.project_options["default_library"] = "static"
        # Disable introspection (requires valac + libgcab) to skip Vala compilation
        tc.project_options["introspection"] = False
        # Add libintl path for static linking (from glib's transitive deps)
        intl_lib = "/storage/Users/currentUser/usr/local/lib"
        if os.path.isdir(intl_lib):
            tc.c_link_args.append(f"-L{intl_lib}")
            tc.c_link_args.append("-lintl")
        tc.generate()
        # Override AR with full path for meson archiver detection
        env = Environment()
        env.define("AR", "/data/service/hnp/bin/llvm-ar")
        env.vars(self).save_script("msitools_env")
        # gnome.mkenums() needs glib_mkenums and glib_genmarshal from pc file.
        # Conan's generated .pc lacks these variables, so we create a wrapper.
        pc_dir = os.path.join(self.build_folder, "conan")
        glib_pc = os.path.join(pc_dir, "glib-2.0.pc")
        if os.path.exists(glib_pc):
            with open(glib_pc) as f:
                content = f.read()
            extra_vars = (
                "\n"
                "glib_genmarshal=glib-genmarshal\n"
                "glib_mkenums=glib-mkenums\n"
            )
            if extra_vars.strip() not in content:
                with open(glib_pc, "a") as f:
                    f.write(extra_vars)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        self.run("ninja", cwd=self.build_folder)

    def package(self):
        # Use DESTDIR to install to package folder
        build_dir = os.path.join(self.source_folder, "build-release")
        if not os.path.isdir(build_dir):
            build_dir = os.path.join(self.build_folder, "build-release")
        destdir = self.package_folder
        self.run(f"DESTDIR={destdir} meson install -C {build_dir}")

    def package_info(self):
        self.cpp_info.libs = ["msi-1.0"]
