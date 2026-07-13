#!/usr/bin/env python3
"""Conan recipe — libgsf 1.14.58 (GNOME Structured File Library).

Build system: autotools (configure + make)
Dependencies: glib-2.0, libxml2 (via @ohpcd/stable)
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class LibgsfConan(ConanFile):
    name = "libgsf"
    version = "1.14.58"
    description = "GNOME Structured File Library for reading and writing structured file formats (OLE2, Zip, etc.)"
    license = "LGPL-2.1-only"
    homepage = "https://gitlab.gnome.org/GNOME/libgsf"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R27: dependencies must reference @ohpcd/stable
        self.requires("glib/2.84.0@ohpcd/stable")
        self.requires("libxml2/2.15.3@ohpcd/stable")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os in ("Linux", "OHOS"):
            tc.extra_cflags.append("-fPIC")
        # Configure args — R1: minimize args
        tc.configure_args.append("--disable-introspection")
        tc.configure_args.append("--without-bz2")
        tc.configure_args.append("--without-gdk-pixbuf")
        # Build static only: libintl is static-only on OHOS
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
        tc.generate()
        # Generate .pc files for dependencies
        pgd = PkgConfigDeps(self)
        pgd.generate()

        # R33: use Conan Environment instead of os.environ global modification
        env = Environment()
        env.define("ACLOCAL", "aclocal-1.16")
        env.define("AUTOMAKE", "automake-1.16")
        env.define("ACLOCAL_PATH", os.path.join(self.source_folder, "m4"))
        env.vars(self, "conanautoreconf").save()

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder

        # Create gtk-doc.make stub
        gtk_doc_make = os.path.join(src, "gtk-doc.make")
        if not os.path.exists(gtk_doc_make):
            with open(gtk_doc_make, "w") as f:
                f.write("# Stub gtk-doc.make\nEXTRA_DIST =\nCLEANFILES =\ndist-check-gtkdoc:\ndocs:\n")

        # Create gtk-doc.m4 stub
        m4_dir = os.path.join(src, "m4")
        os.makedirs(m4_dir, exist_ok=True)
        gtk_doc_m4 = os.path.join(m4_dir, "gtk-doc.m4")
        if not os.path.exists(gtk_doc_m4):
            with open(gtk_doc_m4, "w") as f:
                f.write('dnl Stub gtk-doc.m4\nAC_DEFUN([GTK_DOC_CHECK], [\n  gtk_doc_installed=false\n  AM_CONDITIONAL([ENABLE_GTK_DOC], [test "x$gtk_doc_installed" = "xtrue"])\n])\n')

        # Ensure TMPDIR exists (E002: /tmp is read-only on OHOS)
        tmpdir = os.path.expanduser("~/tmp")
        os.makedirs(tmpdir, exist_ok=True)

        # Run autoreconf with Conan-managed environment (R33)
        self.run("autoreconf -fi -I m4", cwd=src, env="conanautoreconf")

        # Fix umask 077 -> 022 (HMDFS permission issue, E011)
        configure_path = os.path.join(src, "configure")
        if os.path.exists(configure_path):
            with open(configure_path, "r") as f:
                content = f.read()
            content = content.replace("umask 077", "umask 022")
            with open(configure_path, "w") as f:
                f.write(content)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j{}".format(os.cpu_count() or 1)])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["gsf-1"]
        self.cpp_info.includedirs = ["include/libgsf-1"]
        self.cpp_info.requires = ["glib::glib-2.0", "glib::gobject-2.0", "libxml2::libxml2"]
        # System libraries needed by libgsf (zlib for gzip/zip, m for math)
        self.cpp_info.system_libs = ["z", "m"]
