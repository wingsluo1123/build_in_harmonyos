#!/usr/bin/env python3
"""Conan recipe for elfutils 0.195 (Autotools).

Libraries and utilities for handling ELF objects.
License: GPL-3.0-or-later (programs), GPL-2.0-or-later/LGPL-3.0-or-later (libraries)
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ElfutilsConan(ConanFile):
    name = "elfutils"
    version = "0.195"
    description = "Libraries and utilities for handling ELF objects"
    license = "GPL-3.0-or-later"
    homepage = "https://sourceware.org/elfutils/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.configure_args.extend([
                "--disable-silent-rules",
                "--disable-libdebuginfod",
                "--disable-debuginfod",
                "--without-bzlib",
                "--with-lzma",
                "--with-zlib",
                "--with-zstd",
            ])
        tc.generate()

    def _fix_ohos_shell_script(self, file_path):
        """Fix OHOS compatibility issues in shell scripts.

        Key fixes:
        1. mktemp on HMDFS: mktemp-created subdirs can't be written to.
           Replace the entire mktemp block with ac_tmp=. (use current dir).
           Also disable the cleanup trap to prevent rm -fr .
        2. E076: pipe-based commands fail on HarmonyOS (fstat on pipe returns EACCES).
        """
        if not os.path.exists(file_path):
            return
        with open(file_path, 'r') as f:
            content = f.read()

        # Fix 1: Replace mktemp block with using current directory directly.
        # The mktemp -d creates dirs but HMDFS prevents writing files inside them.
        # Using "." (current dir) avoids this since the build dir is writable.
        # We replace the entire tmp creation block.
        content = content.replace(
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&\n'
            '  test -d "$tmp"\n'
            '}  ||\n'
            '{\n'
            '  tmp=./conf$$-$RANDOM\n'
            '  (umask 077 && mkdir "$tmp")\n'
            '} || as_fn_error $? "cannot create a temporary directory in ." "$LINENO" 5\n'
            'ac_tmp=$tmp',
            'tmp=.\n'
            '} || as_fn_error $? "cannot create a temporary directory in ." "$LINENO" 5\n'
            'ac_tmp=$tmp'
        )
        # Also handle the case where mktemp fix was already applied (d=... pattern)
        content = content.replace(
            'tmp=`(umask 077 && d="${TMPDIR:-.}/conf$$-$RANDOM" && (umask 077 && mkdir "$d") && echo "$d") 2>/dev/null` &&\n'
            '  test -d "$tmp"\n'
            '}  ||\n'
            '{\n'
            '  tmp=./conf$$-$RANDOM\n'
            '  (umask 077 && mkdir "$tmp")\n'
            '} || as_fn_error $? "cannot create a temporary directory in ." "$LINENO" 5\n'
            'ac_tmp=$tmp',
            'tmp=.\n'
            '} || as_fn_error $? "cannot create a temporary directory in ." "$LINENO" 5\n'
            'ac_tmp=$tmp'
        )
        # Disable cleanup trap to prevent rm -fr . when ac_tmp=.
        content = content.replace(
            '  { test ! -d "$ac_tmp" || rm -fr "$ac_tmp"; } && exit $exit_status',
            '  exit $exit_status'
        )

        # Fix 2: E076 — pipe-based sed
        content = content.replace(
            'echo "$ac_subst_vars" | sed \'s/.*/&!$&$ac_delim/\'',
            'echo "$ac_subst_vars" >conf$$.sv && sed \'s/.*/&!$&$ac_delim/\' conf$$.sv && rm -f conf$$.sv'
        )
        # Fix 3: E076 — pipe-based grep
        content = content.replace(
            'echo "$ac_subst_vars" | grep -c \'^\'',
            'echo "$ac_subst_vars" >conf$$.gc && grep -c \'^\' conf$$.gc; rm -f conf$$.gc'
        )
        # Fix 4: E076 — pipe-based sed|grep
        content = content.replace(
            'sed -n "s/.*$ac_delim\\$/X/p" conf$$subs.awk | grep -c X',
            'sed -n "s/.*$ac_delim\\$/X/p" conf$$subs.awk >conf$$.gc2 && grep -c X conf$$.gc2; rm -f conf$$.gc2'
        )
        # Fix 5: E076 — echo X | tr
        content = content.replace(
            "echo X | tr X '\\015'",
            "printf 'X\\015' >conf$$.tr && tr X '\\015' <conf$$.tr; rm -f conf$$.tr"
        )

        with open(file_path, 'w') as f:
            f.write(content)

    def build(self):
        apply_conandata_patches(self)

        if self.settings.os == "OHOS":
            # Set TMPDIR to a writable directory for /bin/sh's own temp files
            # (/tmp is read-only on HarmonyOS — E002). The config.status fix
            # uses ac_tmp=. (current dir) so TMPDIR doesn't affect mktemp.
            tmpdir = os.path.expanduser("~/tmp")
            os.makedirs(tmpdir, exist_ok=True)
            os.environ["TMPDIR"] = tmpdir

            # Fix configure script (patches heredoc → config.status)
            configure_path = os.path.join(self.source_folder, "configure")
            if not os.path.exists(configure_path):
                configure_path = os.path.join(os.getcwd(), "configure")
            self._fix_ohos_shell_script(configure_path)

        # Run configure with /bin/sh (not bash) to avoid heredoc pipe issues (E076).
        # Override CONFIG_SHELL, SHELL, GREP, EGREP from the conan profile.
        # Use /bin/grep to avoid harmonybrew grep PCRE2 symbol errors.
        # Use --prefix=/ so that DESTDIR (set by Autotools.install()) works correctly.
        # Note: configure will create config.status and run it. config.status may
        # fail due to HMDFS mktemp issue. We use '|| true' to continue, then fix
        # config.status and re-run it manually.
        configure_args = " ".join([
            "--disable-silent-rules",
            "--disable-libdebuginfod",
            "--disable-debuginfod",
            "--without-bzlib",
            "--with-lzma",
            "--with-zlib",
            "--with-zstd",
            "--prefix=/",
        ])
        self.run(
            f'CONFIG_SHELL=/bin/sh SHELL=/bin/sh '
            f'TMPDIR={os.environ.get("TMPDIR", "$HOME/tmp")} '
            'GREP=/bin/grep EGREP="/bin/grep -E" '
            f'./configure {configure_args} || true'
        )

        # Fix config.status (generated by configure) — apply mktemp + pipe fixes
        config_status = os.path.join(self.source_folder, "config.status")
        if not os.path.exists(config_status):
            config_status = os.path.join(os.getcwd(), "config.status")
        self._fix_ohos_shell_script(config_status)

        # Re-run config.status with fixes applied
        if os.path.exists(config_status):
            self.run(
                f'CONFIG_SHELL=/bin/sh SHELL=/bin/sh '
                f'TMPDIR={os.environ.get("TMPDIR", "$HOME/tmp")} '
                'GREP=/bin/grep EGREP="/bin/grep -E" '
                './config.status'
            )

        autotools = Autotools(self)
        autotools.make(args=["-j2"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["elf", "dw", "asm"]
        self.cpp_info.system_libs = ["z", "zstd", "lzma", "argp", "obstack"]
