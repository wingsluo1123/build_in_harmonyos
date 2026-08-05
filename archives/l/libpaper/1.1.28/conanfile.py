#!/usr/bin/env python3
"""Conan recipe for libpaper 1.1.28 — Autotools (autoreconf + configure + make).

The source tarball only contains configure.ac/Makefile.am (no generated
autotools files), so autoreconf must run to generate them. The 13 patches
are "create" type (diff -ruN against empty files), so the generated files
must be emptied before patching to avoid content duplication.
"""
import os
from conan import ConanFile
from conan.tools.files import get, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibpaperConan(ConanFile):
    name = "libpaper"
    version = "1.1.28"
    description = "Library for handling paper sizes and paper names"
    license = "GPL-2.0"
    homepage = "https://packages.debian.org/source/libpaper"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        # Source tarball has only configure.ac/Makefile.am — bootstrap autotools first.
        self.run("autoreconf --install --force", cwd=self.source_folder)

        # All 13 patches are "create" type (diff -ruN against empty files).
        # The patch command can't apply them to existing non-empty files.
        # Instead, extract patched content directly from patch files.
        patches_dir = os.path.join(self.source_folder, "patches")
        for p in self.conan_data.get("patches", []):
            patch_file = os.path.join(patches_dir, os.path.basename(p["patch_file"]))
            self.run(
                f'target=$(grep "^+++ b/" "{patch_file}" | sed "s|^+++ b/||") && '
                f'grep "^+" "{patch_file}" | grep -v "^+++" | sed "s/^+//" > "$target"',
                cwd=self.source_folder,
            )

        # Fix HarmonyOS umask 077 issue: config.status cannot create temp files
        replace_in_file(self, os.path.join(self.source_folder, "configure"),
                        "umask 000", "umask 022", strict=False)

        # Use Autotools helper (handles triplet, CC, CXX, CFLAGS, LDFLAGS)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["paper"]
        self.cpp_info.set_property("pkg_config_name", "libpaper")
