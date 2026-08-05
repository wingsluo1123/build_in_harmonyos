#!/usr/bin/env python3
"""Conan recipe for libpaper 1.1.28 — Autotools (autoreconf + configure + make).

The source tarball only contains configure.ac/Makefile.am (no generated
autotools files), so autoreconf must run to generate them. The 13 patches
are "create" type (diff -ruN against empty files), so the generated files
must be emptied before patching to avoid content duplication.
"""
import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibpaperConan(ConanFile):
    name = "libpaper"
    version = "1.1.28"
    description = "Library for handling paper sizes and paper names"
    license = "GPL-2.0"
    homepage = "https://packages.debian.org/source/libpaper"
    url = ""

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
            # Extract target path from patch header (+++ b/path), then
            # write patched content (lines starting with +, excluding +++ header)
            self.run(
                f'target=$(grep "^+++ b/" "{patch_file}" | sed "s|^+++ b/||") && '
                f'grep "^+" "{patch_file}" | grep -v "^+++" | sed "s/^+//" > "$target"',
                cwd=self.source_folder,
            )
        # Fix HarmonyOS umask 077 issue: config.status cannot create temp files
        self.run("sed -i 's/umask 077/umask 000/g' configure", cwd=self.source_folder)
        # Run configure directly with all three triplet flags
        self.run(
            "./configure --prefix=/ "
            "--bindir=${prefix}/bin --sbindir=${prefix}/bin "
            "--libdir=${prefix}/lib --includedir=${prefix}/include "
            "--oldincludedir=${prefix}/include "
            "--enable-static --disable-shared "
            "--build=aarch64-linux --host=aarch64-linux --target=aarch64-linux",
            cwd=self.source_folder,
        )
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        self.run(f"make install DESTDIR={self.package_folder}", cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["paper"]
