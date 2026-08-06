#!/usr/bin/env python3
"""Conan recipe — json-glib 1.6.6 (Meson).

json-glib is a library providing JSON serialization and deserialization
support for GLib. It uses the Meson build system and depends on GLib (glib2).
Adapted to HarmonyOS PC (aarch64).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


class JsonglibConan(ConanFile):
    name = "json-glib"
    version = "1.6.6"
    description = "A library providing JSON serialization and deserialization support for GLib"
    license = "LGPL-2.1-or-later"
    homepage = "https://wiki.gnome.org/Projects/JsonGlib"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    # Generate .pc files for Conan deps (glib2 → glib-2.0.pc, zlib, pcre2)
    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # glib2 provides glib-2.0, gobject-2.0, gio-2.0, gmodule-2.0,
        # gthread-2.0, ffi, intl — all needed by json-glib (library + tools).
        self.requires("glib2/2.88.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        glib2 = self.dependencies["glib2"]
        glib2_prefix = glib2.package_folder

        # Add glib2's bin/ to PATH so meson's gnome.mkenums() can find
        # glib-mkenums (a python3 script shipped with the glib2 package).
        glib2_bin = os.path.join(glib2_prefix, "bin")
        if os.path.isdir(glib2_bin):
            os.environ["PATH"] = glib2_bin + os.pathsep + os.environ.get("PATH", "")

        # Fix AR/AS/STRIP/NM/RANLIB — same issue as glib2: llvm-* names
        # exported by CI but not on PATH; pin real GNU tools.
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {name: shutil.which(name) for name in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(
                f"Required build tools not found in PATH: {', '.join(missing)}"
            )

        # glib2's Conan recipe declares only pkg_config_name="glib-2.0", so
        # PkgConfigDeps generates only glib-2.0.pc. But meson needs gio-2.0.pc,
        # gobject-2.0.pc, etc. The glib2 package ships these in
        # lib/pkgconfig/ with prefix=/ (broken). Copy them to the generators
        # folder with the correct prefix.
        # glib2's Conan recipe declares only pkg_config_name="glib-2.0", so
        # PkgConfigDeps generates only glib-2.0.pc. But that generated .pc file
        # lacks custom variables like glib_mkenums that gnome.mkenums() needs.
        # The glib2 package ships proper .pc files (gio-2.0.pc, gobject-2.0.pc,
        # glib-2.0.pc with glib_mkenums var, etc.) in lib/pkgconfig/ with
        # prefix=/ (broken). Copy ALL of them to the generators folder with the
        # correct prefix, overwriting the PkgConfigDeps-generated ones.
        pc_src_dir = os.path.join(glib2_prefix, "lib", "pkgconfig")
        if os.path.isdir(pc_src_dir):
            for pc_file in os.listdir(pc_src_dir):
                if not pc_file.endswith(".pc"):
                    continue
                src_path = os.path.join(pc_src_dir, pc_file)
                with open(src_path) as f:
                    content = f.read()
                # Fix prefix=/ to the actual glib2 package directory
                content = content.replace("prefix=/", f"prefix={glib2_prefix}")
                dst_path = os.path.join(self.generators_folder, pc_file)
                with open(dst_path, "w") as f:
                    f.write(content)
            # Add generators folder to PKG_CONFIG_PATH so meson finds all .pc files
            os.environ["PKG_CONFIG_PATH"] = (
                self.generators_folder + os.pathsep
                + os.environ.get("PKG_CONFIG_PATH", "")
            )

        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        tc.strip = tools["strip"]
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # Disable features not available on OHOS
        tc.project_options["introspection"] = "disabled"
        tc.project_options["gtk_doc"] = "disabled"
        tc.project_options["tests"] = False
        tc.project_options["man"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["json-glib-1.0"]
        self.cpp_info.includedirs = ["include/json-glib-1.0"]
        self.cpp_info.set_property("pkg_config_name", "json-glib-1.0")
        self.cpp_info.set_property("cmake_target_name", "json-glib::json-glib")
