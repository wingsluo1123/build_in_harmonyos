#!/usr/bin/env python3
"""Conan recipe for rpki-client 9.6 — RPKI validation tool (OpenBSD portable).

Build system: autotools (configure.ac + Makefile.am)
Product: command-line binary (sbin_PROGRAMS)

Platform notes:
  - HarmonyOS is not recognized by config.guess; we override --host to
    aarch64-unknown-linux-gnu so configure detects Linux compatibility.
  - HMDFS filesystem restricts temp-file creation (umask 077 dirs and
    mktemp in cwd); configure and config.status are patched to use
    mktemp -d (TMPDIR) and umask 022. File writes use write-to-TMPDIR-
    then-copy because HMDFS does not support atomic in-place replacement.
  - Dependency paths are passed as configure VAR=VALUE arguments because
    AutotoolsToolchain doesn't auto-inject conan dep paths into CPPFLAGS/LDFLAGS.
"""
import os
import glob
import shutil
import tempfile

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


def _hmfs_replace(filepath, replacements):
    """HMDFS-safe file replacement: write to TMPDIR then copy back."""
    if not os.path.isfile(filepath):
        return
    with open(filepath, encoding="utf-8", errors="ignore") as f:
        text = f.read()
    for old, new in replacements:
        text = text.replace(old, new)
    tmpdir = os.environ.get("TMPDIR", "/tmp")
    fd, tmpfile = tempfile.mkstemp(dir=tmpdir, suffix=".patched")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        shutil.copy2(tmpfile, filepath)
    finally:
        if os.path.exists(tmpfile):
            os.unlink(tmpfile)


class RpkiClientConan(ConanFile):
    name = "rpki-client"
    version = "9.6"
    description = "RPKI (Resource Public Key Infrastructure) validation tool for BGP route origin validation"
    license = "ISC"
    homepage = "https://rpki-client.org"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libressl/3.9.1")
        self.requires("musl-fts/1.2.7")
        self.requires("expat/2.8.2")
        self.requires("zlib/1.3.1")
        self.requires("rsync/3.3.0")

    def build_requirements(self):
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)

        # Ensure TMPDIR is set (HarmonyOS /tmp is read-only)
        if not os.environ.get("TMPDIR"):
            os.environ["TMPDIR"] = os.path.expanduser("~/tmp")
        os.makedirs(os.environ["TMPDIR"], exist_ok=True)

        self._setup_build_tools()

        # Add rsync (runtime dep) to PATH for configure's rsync check
        try:
            rsync_dep = self.dependencies["rsync"]
            if rsync_dep.package_folder:
                rsync_bin = os.path.join(rsync_dep.package_folder, "bin")
                if os.path.isdir(rsync_bin):
                    os.environ["PATH"] = rsync_bin + ":" + os.environ.get("PATH", "")
        except (KeyError, Exception):
            pass

        # Step 1: autoreconf
        os.makedirs(os.path.join(self.source_folder, "m4"), exist_ok=True)
        self.run("autoreconf -i -f", cwd=self.source_folder)

        # Step 2: Patch configure for HMDFS
        configure_path = os.path.join(self.source_folder, "configure")
        _hmfs_replace(configure_path, [
            ('mktemp -d "./confXXXXXX"', "mktemp -d"),
            ("tmp=./conf$$-$RANDOM", "tmp=${TMPDIR:-/tmp}/conf$$-$RANDOM"),
            ("umask 077", "umask 022"),
        ])
        os.chmod(configure_path, 0o755)

        # Step 3: Create custom config.guess
        cg = os.path.join(self.source_folder, "config.guess")
        with open(cg, "w") as f:
            f.write('#!/bin/sh\necho "aarch64-unknown-linux-gnu"\nexit 0\n')
        os.chmod(cg, 0o755)

        # Step 4: Build configure command with dependency paths as VAR=VALUE
        cppflags, ldflags = self._get_dep_paths()
        cc = os.environ.get("CC", "clang")
        cflags = "-fPIC -O2 -D_DEFAULT_SOURCE -D_BSD_SOURCE -D_GNU_SOURCE"
        libs = "-ltls -lssl -lcrypto -lfts -lexpat -lz -lpthread -ldl"

        configure_cmd = (
            f'./configure '
            f'--host=aarch64-unknown-linux-gnu '
            f'--prefix={self.package_folder} '
            f'--with-tal-dir={self.package_folder}/etc/rpki '
            f'--with-base-dir=/usr/local/cache/rpki-client '
            f'--with-output-dir=/usr/local/db/rpki-client '
            f'CC="{cc}" '
            f'CFLAGS="{cflags}" '
            f'CPPFLAGS="{cppflags}" '
            f'LDFLAGS="{ldflags}" '
            f'LIBS="{libs}"'
        )

        # Step 5: Run configure
        self.run(configure_cmd, cwd=self.source_folder)

        # Step 6: Patch config.status for HMDFS
        cs = os.path.join(self.source_folder, "config.status")
        _hmfs_replace(cs, [("umask 077", "umask 022")])
        if os.path.isfile(cs):
            os.chmod(cs, 0o755)

        # Step 7: Run config.status to regenerate Makefiles
        self.run("./config.status", cwd=self.source_folder)

        # Step 8: Build (j1 — HMDFS doesn't support mkfifo for jobserver)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        self.run("make install", cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []

    # ── Helpers ──────────────────────────────────────────────────

    def _get_dep_paths(self):
        """Get CPPFLAGS and LDFLAGS from conan dependencies."""
        cppflags = []
        ldflags = []
        for dep_name in ["libressl", "musl-fts", "expat", "zlib"]:
            try:
                dep = self.dependencies[dep_name]
            except (KeyError, Exception):
                continue
            pkg = dep.package_folder
            if not pkg:
                continue
            inc = os.path.join(pkg, "include")
            lib = os.path.join(pkg, "lib")
            if os.path.isdir(inc):
                cppflags.append(f"-I{inc}")
            if os.path.isdir(lib):
                ldflags.append(f"-L{lib}")
        return " ".join(cppflags), " ".join(ldflags)

    def _setup_build_tools(self):
        """Set up automake/libtool environment from conan cache."""
        conan_home = os.environ.get("CONAN_HOME", os.path.expanduser("~/.conan2"))

        automake_dir = self._find_pkg_dir(conan_home, "automake")
        libtool_dir = self._find_pkg_dir(conan_home, "libtool")

        if automake_dir:
            os.environ["PERL5LIB"] = os.path.join(automake_dir, "share", "automake-1.18")
            os.environ["ACLOCAL_PATH"] = os.path.join(automake_dir, "share", "aclocal")
            os.environ["PATH"] = os.path.join(automake_dir, "bin") + ":" + os.environ.get("PATH", "")

        if libtool_dir:
            os.environ["_lt_pkgdatadir"] = os.path.join(libtool_dir, "share", "libtool")
            os.environ["ACLOCAL_PATH"] = (
                os.environ.get("ACLOCAL_PATH", "") + ":" +
                os.path.join(libtool_dir, "share", "aclocal")
            )
            os.environ["PATH"] = os.path.join(libtool_dir, "bin") + ":" + os.environ.get("PATH", "")

            m4_dir = os.path.join(libtool_dir, "share", "libtool", "m4")
            if not os.path.isdir(m4_dir):
                os.makedirs(m4_dir, exist_ok=True)
                aclocal_dir = os.path.join(libtool_dir, "share", "aclocal")
                if os.path.isdir(aclocal_dir):
                    for f in os.listdir(aclocal_dir):
                        if f.endswith(".m4"):
                            shutil.copy(os.path.join(aclocal_dir, f), m4_dir)

    @staticmethod
    def _find_pkg_dir(conan_home, name):
        """Find conan package directory for a build tool."""
        pattern = os.path.join(conan_home, "p", f"{name}*")
        matches = sorted(glob.glob(pattern))
        for match in matches:
            pkg_dir = os.path.join(match, "p")
            if os.path.isdir(pkg_dir):
                return pkg_dir
        return ""
