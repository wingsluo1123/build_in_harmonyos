#!/usr/bin/env python3
"""Conan recipe — libgsf 1.14.58 (GNOME Structured File Library).

Build system: autotools (configure + make)
Dependencies: glib-2.0, libxml2 (via @ohpcd/stable)
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
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
        # Try local copy first (network may be unavailable on OHOS)
        import hashlib
        local_tarball = os.path.expanduser("~/tmp/builds/libgsf-1.14.58.tar.gz")
        if os.path.exists(local_tarball):
            sources = self.conan_data["sources"]
            expected_sha = sources.get("sha256", "")
            if expected_sha and expected_sha != "REPLACE_WITH_ACTUAL_SHA256":
                actual_sha = hashlib.sha256(open(local_tarball, "rb").read()).hexdigest()
                if actual_sha != expected_sha:
                    raise Exception(f"SHA256 mismatch: expected {expected_sha}, got {actual_sha}")
            import tarfile
            with tarfile.open(local_tarball, "r:gz") as tf:
                try:
                    tf.extractall(self.source_folder, filter='data')
                except TypeError:
                    tf.extractall(self.source_folder)
            entries = os.listdir(self.source_folder)
            if len(entries) == 1 and os.path.isdir(os.path.join(self.source_folder, entries[0])):
                nested = os.path.join(self.source_folder, entries[0])
                for item in os.listdir(nested):
                    shutil.move(os.path.join(nested, item), os.path.join(self.source_folder, item))
                os.rmdir(nested)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os in ("Linux", "OHOS"):
            tc.extra_cflags.append("-fPIC")
        # Ensure system libintl can be found by linker
        tc.extra_ldflags.append("-L/storage/Users/currentUser/usr/local/lib")
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

        # Set up autotools environment
        env_vars = {
            "ACLOCAL": "aclocal-1.16",
            "AUTOMAKE": "automake-1.16",
            "ACLOCAL_PATH": os.path.join(src, "m4") + ":/storage/Users/currentUser/usr/local/share/aclocal:/data/service/hnp/pkg-config.org/pkg-config_0.29.2/share/aclocal",
            "TMPDIR": os.path.expanduser("~/tmp"),
        }
        for k, v in env_vars.items():
            os.environ[k] = v

        # Run autoreconf in source folder
        self.run("autoreconf -fi -I m4", cwd=src, env="conanbuild")

        # Fix umask 077 -> 022 (HMDFS permission issue)
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
