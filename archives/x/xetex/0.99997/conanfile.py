#!/usr/bin/env python3
"""Conan recipe for XeTeX 0.99997 (xelatex).

XeTeX is a TeX typesetting engine with Unicode and system font support.
Build system: custom (autotools + manual compilation of bundled deps).

Key HMDFS workarounds:
- umask 077 → 022 (HMDFS setgid prevents writing to 700 dirs)
- config.guess: add HarmonyOS to Linux pattern
- Subdirectories: local build-aux (../../ traversal unreliable on HMDFS)
- ac_cv_header_stdc=yes (AC_HEADER_STDC fails on OHOS)
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class XetexConan(ConanFile):
    name = "xetex"
    version = "0.99997"
    description = "XeTeX typesetting engine, provides xelatex command-line tool"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/TeX-Live/xetex"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("freetype/2.14.3")
        self.requires("zlib/1.3.1")
        self.requires("expat/2.8.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # XeTeX uses custom build script, not standard CMake
        # The actual build is handled in build() method
        env = Environment()
        env.define("CC", "clang")
        env.define("CXX", "clang++")
        env.define("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        env.define("TMPDIR", os.path.join(self.build_folder, "tmp"))
        env.define("ac_cv_header_stdc", "yes")
        env.define("AUTOCONF", "/data/service/hnp/bin/autoconf")
        env.define("AUTOHEADER", "/data/service/hnp/bin/autoheader")
        env.define("AUTOM4TE", "/data/service/hnp/bin/autom4te")
        env.vars(self).save_script("xetex_env")

    def build(self):
        src = self.source_folder
        bld = self.build_folder
        os.makedirs(os.path.join(bld, "tmp"), exist_ok=True)

        # 1. Copy build-aux files from autoconf installation
        #    Upstream tarball doesn't ship build-aux/; normally automake --add-missing
        #    provides these, but automake is not available on OHOS.
        build_aux = os.path.join(src, "source", "build-aux")
        os.makedirs(build_aux, exist_ok=True)
        autoconf_aux = os.path.join(
            os.path.dirname(os.path.dirname(os.path.realpath(
                shutil.which("autoconf") or "/data/service/hnp/bin/autoconf"))),
            "share", "autoconf", "build-aux")
        for fname in ("install-sh", "config.guess", "config.sub"):
            src_file = os.path.join(autoconf_aux, fname)
            if os.path.isfile(src_file):
                shutil.copy2(src_file, os.path.join(build_aux, fname))
                os.chmod(os.path.join(build_aux, fname), 0o755)

        # 2. Fix config.guess for HarmonyOS
        config_guess = os.path.join(build_aux, "config.guess")
        if os.path.exists(config_guess):
            self._replace_in_file(config_guess, "Linux|GNU|GNU/*)", "Linux|GNU|GNU/*|HarmonyOS)")

        # 3. Fix umask 077 → 022 in all configure scripts (HMDFS workaround)
        self._fix_umask_recursive(src)

        # 4. Fix AC_CONFIG_AUX_DIR paths in subdirectories
        self._fix_aux_dirs(src)

        # 5. Generate configure script (automake not available on OHOS)
        #    Create aclocal.m4 with automake macro stubs, then run autoconf directly.
        source_dir = os.path.join(src, "source")
        aclocal_m4 = os.path.join(source_dir, "aclocal.m4")
        with open(aclocal_m4, "w") as f:
            f.write(
                "m4_pattern_allow([m4_sinclude])\n"
                "AC_DEFUN([AM_INIT_AUTOMAKE], [])\n"
                "AC_DEFUN([AM_MAINTAINER_MODE], [])\n"
                "AC_DEFUN([AM_AUTOMAKE_VERSION], [])\n"
                "AC_DEFUN([AM_CONDITIONAL], [])\n"
                "AC_DEFUN([AM_COND_IF], [])\n"
                "AC_DEFUN([AM_COND_ELSE], [])\n"
                "AC_DEFUN([AM_COND_ENDIF], [])\n"
                "AC_DEFUN([AM_SILENT_RULES], [])\n"
                "AC_DEFUN([AM_PROG_AR], [])\n"
                "AC_DEFUN([AM_PROG_CC_C_O], [])\n"
                "AC_DEFUN([AM_PROG_CXX_C_O], [])\n"
                "AC_DEFUN([AM_MISSING_PROG], [])\n"
                "AC_DEFUN([AM_PROG_INSTALL], [])\n"
                "AC_DEFUN([AM_PROG_MKDIR_P], [])\n"
                "AC_DEFUN([AM_SUBST_NOTMAKE], [])\n"
                "AC_DEFUN([AM_MAKEFILE_INCLUDE], [])\n"
                "AC_DEFUN([AM_PROG_LIBTOOL], [])\n"
                "AC_DEFUN([AM_DISABLE_SHARED], [])\n"
                "AC_DEFUN([AM_DISABLE_STATIC], [])\n"
                "AC_DEFUN([AM_ENABLE_SHARED], [])\n"
                "AC_DEFUN([AM_ENABLE_STATIC], [])\n"
                "AC_DEFUN([AM_PROG_LD], [])\n"
                "AC_DEFUN([AM_PROG_NM], [])\n"
                "AC_DEFUN([AM_PROG_AS], [])\n"
                "AC_DEFUN([AM_PROG_FC_C_O], [])\n"
                "AC_DEFUN([AM_PROG_MOC], [])\n"
                "AC_DEFUN([AM_GNU_GETTEXT], [])\n"
                "AC_DEFUN([AM_GNU_GETTEXT_INTL_SUBDIR], [])\n"
                "AC_DEFUN([AM_ICONV], [])\n"
                "AC_DEFUN([AM_NLS], [])\n"
                "AC_DEFUN([AM_DEFAULT_VERBOSITY], [])\n"
                "AC_DEFUN([AM_DISTCHECK_CONFIGURE_FLAGS], [])\n"
                "AC_DEFUN([AM_EXTRA_RECURSIVE_TARGETS], [])\n"
            )
        # Create Makefile.in from Makefile.am (automake not available)
        for dirpath, _, filenames in os.walk(source_dir):
            if "Makefile.am" in filenames and "Makefile.in" not in filenames:
                shutil.copy(os.path.join(dirpath, "Makefile.am"),
                            os.path.join(dirpath, "Makefile.in"))
        self._run("cd source && autoconf --force", cwd=src)

        # 6. Configure and build
        conf_opts = " ".join([
            "--build=aarch64-unknown-linux-gnu",
            "--enable-build-in-source-tree",
            "--disable-all-pkgs",
            "--disable-shared",
            "--enable-largefile",
            "--enable-silent-rules",
            "--enable-xetex",
            "--without-system-ptexenc",
            "--without-system-kpathsea",
            "--without-mf-x-toolkit",
            "--without-x",
            "--with-system-freetype2",
            "--with-system-libpng",
            "--with-system-teckit",
            "--with-system-zlib",
            "--with-system-icu",
            "--with-system-graphite2",
            "--with-system-harfbuzz",
            "--with-system-poppler",
            f"--prefix={bld}/install",
        ])
        self._run(f"cd source && ./configure {conf_opts}", cwd=src)
        self._run("cd source && make -j1", cwd=src)
        self._run("cd source && make -C texk/web2c xetex", cwd=src)

    def package(self):
        src = self.source_folder
        copy(self, "xetex", src=os.path.join(src, "source", "texk", "web2c"),
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]

    def _fix_umask_recursive(self, root):
        """Replace umask 077 with umask 022 in all configure scripts."""
        for dirpath, _, filenames in os.walk(root):
            for f in filenames:
                if f == "configure":
                    filepath = os.path.join(dirpath, f)
                    self._replace_in_file(filepath, "umask 077", "umask 022")

    def _fix_aux_dirs(self, root):
        """Create local build-aux in subdirectories and fix AC_CONFIG_AUX_DIR."""
        source_dir = os.path.join(root, "source")
        build_aux = os.path.join(source_dir, "build-aux")
        for dirpath, _, filenames in os.walk(source_dir):
            if "configure.ac" in filenames:
                ac_file = os.path.join(dirpath, "configure.ac")
                content = open(ac_file).read()
                if "AC_CONFIG_AUX_DIR" in content:
                    local_aux = os.path.join(dirpath, "build-aux")
                    os.makedirs(local_aux, exist_ok=True)
                    for f in os.listdir(build_aux):
                        shutil.copy(os.path.join(build_aux, f), local_aux)

    def _replace_in_file(self, filepath, old, new):
        content = open(filepath).read()
        if old in content:
            content = content.replace(old, new)
            open(filepath, "w").write(content)

    def _run(self, cmd, cwd=None):
        from conan.tools.files import save
        self.run(cmd, cwd=cwd or self.source_folder)
