#!/usr/bin/env python3
"""Conan recipe for elfutils 0.195 (Autotools).

Libraries and utilities for handling ELF objects.
License: GPL-3.0-or-later (programs), GPL-2.0-or-later/LGPL-3.0-or-later (libraries)
"""
import os
import urllib.request

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ElfutilsConan(ConanFile):
    name = "elfutils"
    version = "0.195"
    description = "Libraries and utilities for handling ELF objects"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/sourceware-org/elfutils"
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
                "--without-lzma",
                "--with-zlib",
                "--without-zstd",
            ])
        tc.generate()


    def _build_musl_deps(self):
        """Build musl-compatible libraries (argp, fts, obstack) from source."""
        prefix = os.path.expanduser('~/usr/local')
        libdir = os.path.join(prefix, 'lib')
        incdir = os.path.join(prefix, 'include')
        os.makedirs(libdir, exist_ok=True)
        os.makedirs(incdir, exist_ok=True)

        build_dir = os.path.join(os.getcwd(), '_musl_deps')
        os.makedirs(build_dir, exist_ok=True)

        # --- argp-standalone ---
        argp_url = 'https://raw.githubusercontent.com/argp-standalone/argp-standalone/1.5.0'
        argp_srcs = [
            'argp-parse.c', 'argp-fmtstream.c', 'argp-help.c',
            'argp-ba.c', 'argp-eexst.c', 'argp-pv.c', 'argp-pvh.c',
            'mempcpy.c', 'strcasecmp.c', 'strchrnul.c', 'strndup.c',
        ]
        argp_hdrs = ['argp.h', 'argp-fmtstream.h', 'argp-namefrob.h']
        for f in argp_srcs + argp_hdrs:
            dest = os.path.join(build_dir, f)
            if not os.path.exists(dest):
                urllib.request.urlretrieve(f'{argp_url}/{f}', dest)

        # Minimal config.h for argp-standalone
        with open(os.path.join(build_dir, 'config.h'), 'w') as f:
            f.write('#define HAVE_STRCASECMP 1\n')
            f.write('#define HAVE_STRNDUP 1\n')
            f.write('#define HAVE_STRCHRNUL 1\n')

        # Compile argp sources
        obj_files = []
        for src in argp_srcs:
            obj = src.replace('.c', '.o')
            self.run(f'clang -c -fPIC -O2 -I{build_dir} -DHAVE_CONFIG_H '
                     f'-o {build_dir}/{obj} {build_dir}/{src}')
            obj_files.append(f'{build_dir}/{obj}')
        self.run(f'llvm-ar cr {libdir}/libargp.a {" ".join(obj_files)}')
        self.run(f'llvm-ranlib {libdir}/libargp.a')

        # --- musl-fts ---
        fts_url = 'https://raw.githubusercontent.com/void-linux/musl-fts/v1.2.7'
        for f in ['fts.c', 'fts.h']:
            dest = os.path.join(build_dir, f)
            if not os.path.exists(dest):
                urllib.request.urlretrieve(f'{fts_url}/{f}', dest)
        self.run(f'clang -c -fPIC -O2 -I{build_dir} -o {build_dir}/fts.o {build_dir}/fts.c')
        self.run(f'llvm-ar cr {libdir}/libfts.a {build_dir}/fts.o')
        self.run(f'llvm-ranlib {libdir}/libfts.a')

        # --- musl-obstack ---
        obs_url = 'https://raw.githubusercontent.com/pullmoll/musl-obstack/master'
        for f in ['obstack.c', 'obstack.h', 'obstack_printf.c']:
            dest = os.path.join(build_dir, f)
            if not os.path.exists(dest):
                urllib.request.urlretrieve(f'{obs_url}/{f}', dest)
        self.run(f'clang -c -fPIC -O2 -I{build_dir} -o {build_dir}/obstack.o {build_dir}/obstack.c')
        self.run(f'clang -c -fPIC -O2 -I{build_dir} -o {build_dir}/obstack_printf.o {build_dir}/obstack_printf.c')
        self.run(f'llvm-ar cr {libdir}/libobstack.a {build_dir}/obstack.o {build_dir}/obstack_printf.o')
        self.run(f'llvm-ranlib {libdir}/libobstack.a')

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
            self._build_musl_deps()

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
            "--without-lzma",
            "--with-zlib",
            "--without-zstd",
            "--prefix=/",
        ])
        self.run(
            f'CONFIG_SHELL=/bin/sh SHELL=/bin/sh '
            f'TMPDIR={os.environ.get("TMPDIR", "$HOME/tmp")} '
            'GREP=/bin/grep EGREP="/bin/grep -E" '
            'ac_cv_search_argp_parse="-largp -lobstack" '
            'ac_cv_search_fts_close=-lfts '
            'ac_cv_search__obstack_free=-lobstack '
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
        self.cpp_info.system_libs = ["z", "argp", "obstack", "fts"]
