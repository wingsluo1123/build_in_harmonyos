#!/usr/bin/env python3
"""Conan recipe for mutt 2.2.16 — Autotools (configure + make).

mutt is a command-line email client (application, not a library).
Build product: executables (mutt, mutt_pgpring, pgpewrap, flea, smime_keys).

OHOS CI workers ship the ncurses runtime library but NOT the development
headers, so the ncurses headers and a matching static libncursesw.a are
bundled under res/ (same approach as nudoku/bitwise).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MuttConan(ConanFile):
    name = "mutt"
    version = "2.2.16"
    description = "Mutt is a small but very powerful text-based email client"
    license = "GPL-2.0-or-later"
    homepage = "http://www.mutt.org/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # Bundle ncurses headers + static lib (res/)
        res_src = os.path.join(self.recipe_folder, "res")
        if os.path.isdir(res_src):
            res_dst = os.path.join(self.export_folder, "res")
            if os.path.exists(res_dst):
                shutil.rmtree(res_dst)
            shutil.copytree(res_src, res_dst)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # Workaround: export_conandata_patches creates PATCHES dir, but mutt
        # source tarball also has a PATCHES file. Move dir out before extract.
        patches_dir = os.path.join(self.source_folder, "PATCHES")
        patches_backup = os.path.join(self.source_folder, "..", "_patches_backup")
        if os.path.isdir(patches_dir):
            shutil.move(patches_dir, patches_backup)
        get(self, **self.conan_data["sources"], strip_root=True)
        # Remove PATCHES file from mutt source, restore PATCHES dir
        if os.path.isdir(patches_backup):
            if os.path.exists(patches_dir) or os.path.islink(patches_dir):
                if os.path.isdir(patches_dir):
                    shutil.rmtree(patches_dir)
                else:
                    os.remove(patches_dir)
            shutil.move(patches_backup, patches_dir)
        # Copy bundled ncurses headers/lib from export folder to source folder
        res_src = os.path.join(self.export_sources_folder, "res") \
            if hasattr(self, 'export_sources_folder') else None
        if not res_src or not os.path.isdir(res_src):
            # Fallback: try relative path
            export_dir = os.path.join(os.path.dirname(self.source_folder), "e")
            res_src = os.path.join(export_dir, "res")
        if os.path.isdir(res_src):
            res_dst = os.path.join(self.source_folder, "res")
            if os.path.exists(res_dst):
                shutil.rmtree(res_dst)
            shutil.copytree(res_src, res_dst)

    def generate(self):
        tc = AutotoolsToolchain(self)
        res_dir = os.path.join(self.source_folder, "res")
        if os.path.isdir(res_dir):
            # Pass as configure args (takes precedence over env vars)
            tc.configure_args.append(f"CPPFLAGS=-I{res_dir}/headers")
            tc.configure_args.append(f"LDFLAGS=-L{res_dir}/lib")
        tc.configure_args.append("--with-curses")
        tc.configure_args.append("--with-mailpath=/var/mail")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
