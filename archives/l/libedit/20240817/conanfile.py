#!/usr/bin/env python3
"""Conan recipe for libedit 20240808-3.1 — Autotools project.

libedit is a line editing library for interactive command-line programs.
It provides the BSD-licensed editline and readline compatible API.

Fixes for OHOS/HMDFS:
- TMPDIR: set to build_folder/tmp (/tmp is erofs read-only)
- config.status: umask 077 creates mode 0700 dirs that HMDFS can't write to;
  the build() method patches configure to use umask 022 before running it.
- ncurses: use system libncursesw.a via NCURSES_ROOT/NCURSES_PREFIX env vars.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibeditConan(ConanFile):
    name = "libedit"
    version = "20240808-3.1"
    description = "BSD-licensed line editing library (editline/readline replacement)"
    license = "BSD-3-Clause"
    homepage = "https://thrysoee.dk/editline/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--disable-examples")

        # ── ncurses header stub for OHOS ──
        # OHOS CI lacks ncurses-devel headers. We generate a minimal stub
        # curses.h that provides the termcap function declarations libedit
        # needs at configure-time and compile-time. Linking uses the system's
        # libncursesw.so.6 at /usr/lib/libncursesw.so.6.
        ncurses_stub_dir = os.path.join(self.build_folder, "ncurses_stub")
        ncurses_stub_include = os.path.join(ncurses_stub_dir, "include")
        os.makedirs(ncurses_stub_include, exist_ok=True)
        stub_header = os.path.join(ncurses_stub_include, "curses.h")
        if not os.path.exists(stub_header):
            with open(stub_header, "w") as f:
                f.write("""/* Minimal curses.h stub for OHOS — provides termcap
 * declarations that libedit needs. Real curses types are
 * not needed; libedit only calls termcap functions. */
#ifndef __CURSES_STUB_H
#define __CURSES_STUB_H

#define HAVE_NCURSES_H 1

typedef unsigned int bool;
#define TRUE 1
#define FALSE 0

/* Termcap entry functions */
extern int tgetent(char *, const char *);
extern int tgetflag(char *);
extern int tgetnum(char *);
extern char *tgetstr(char *, char **);
extern char *tgoto(const char *, int, int);
extern int tputs(const char *, int, int (*)(int));

/* Standard curses types */
typedef int WINDOW;
typedef unsigned int chtype;

extern WINDOW *initscr(void);
extern int endwin(void);
extern int refresh(void);
extern int clearok(WINDOW *, bool);
extern int clear(void);
extern int move(int, int);
extern int addch(const chtype);
extern int addstr(const char *);
extern int printw(const char *, ...);
extern int getch(void);

#endif /* __CURSES_STUB_H */
""")
        tc.extra_cflags.append(f"-I{ncurses_stub_include}")
        tc.extra_cflags.append("-DHAVE_NCURSES_H=1")

        # Also try NCURSES_ROOT / NCURSES_PREFIX (for local developer setups)
        ncurses_root = os.environ.get("NCURSES_ROOT") or os.environ.get("NCURSES_PREFIX")
        ncurses_include = os.environ.get("NCURSES_INCLUDE")
        if ncurses_root:
            inc_dir = os.path.join(ncurses_root, "include")
            lib_dir = os.path.join(ncurses_root, "lib")
            if os.path.isdir(inc_dir):
                tc.extra_cflags.append(f"-I{inc_dir}")
            if os.path.isdir(lib_dir):
                tc.extra_ldflags.append(f"-L{lib_dir}")
        if ncurses_include and os.path.isdir(ncurses_include):
            tc.extra_cflags.append(f"-I{ncurses_include}")
        # Define __STDC_ISO_10646__ to avoid chartype.h #error (replaces removed 0010 patch)
        tc.extra_cflags.append("-D__STDC_ISO_10646__")
        # Link against ncursesw (system library at /usr/lib/libncursesw.so.6)
        tc.extra_ldflags.append("-lncursesw")
        tc.generate()

    def build(self):
        # ── Fix 1: ncurses symlink ──
        ncurses_root = os.environ.get("NCURSES_ROOT") or os.environ.get("NCURSES_PREFIX")
        if ncurses_root:
            lib_dir = os.path.join(ncurses_root, "lib")
            libncurses = os.path.join(lib_dir, "libncurses.a")
            libncursesw = os.path.join(lib_dir, "libncursesw.a")
            if not os.path.exists(libncurses) and os.path.exists(libncursesw):
                os.symlink("libncursesw.a", libncurses)
                self.output.info(f"Created symlink: libncurses.a -> libncursesw.a")

        # ── Fix 2: TMPDIR for /tmp erofs — use build_folder/tmp ──
        # Capture old TMPDIR inside try so recovery is always paired
        old_tmpdir = os.environ.get("TMPDIR")
        try:
            writable_tmp = os.path.join(self.build_folder, "tmp")
            os.makedirs(writable_tmp, exist_ok=True)
            os.environ["TMPDIR"] = writable_tmp

            # ── Fix 3: patch configure to use umask 022 instead of 077 ──
            # On HMDFS, umask 077 creates mode 0700 dirs that can't be written to.
            configure_path = os.path.join(self.source_folder, "configure")
            if os.path.exists(configure_path):
                with open(configure_path) as f:
                    content = f.read()
                original = 'umask 077 && mktemp -d "./confXXXXXX"'
                replacement = 'umask 022 && mktemp -d "./confXXXXXX"'
                if original in content:
                    content = content.replace(original, replacement)
                    with open(configure_path, "w") as f:
                        f.write(content)
                    self.output.info("Patched configure: umask 077 -> 022 for temp dir")
                else:
                    self.output.warning("umask 077 pattern not found in configure")

            # ── Fix 4: termcap function declarations for ncurses without termcap.h ──
            # terminal.c declares tgetent/tgoto/tgetflag/tgetnum/tgetstr/tputs
            # only for __sun; OHOS has them in the ncurses library but not declared
            # in the headers (no termcap.h). We use feature-based detection:
            # HAVE_NCURSES_H && !HAVE_TERMCAP_H instead of platform macro __OHOS__.
            terminal_c = os.path.join(self.source_folder, "src", "terminal.c")
            if os.path.exists(terminal_c):
                with open(terminal_c) as f:
                    content = f.read()
                old_guard = '#if defined(__sun)'
                new_guard = '#if defined(__sun) || (defined(HAVE_NCURSES_H) && !defined(HAVE_TERMCAP_H))'
                if old_guard in content:
                    content = content.replace(old_guard, new_guard)
                    with open(terminal_c, "w") as f:
                        f.write(content)
                    self.output.info("Patched terminal.c: added feature-based termcap decl guard (HAVE_NCURSES_H && !HAVE_TERMCAP_H)")
                else:
                    self.output.warning("__sun guard not found in terminal.c")

            apply_conandata_patches(self)
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j1"])
        finally:
            if old_tmpdir:
                os.environ["TMPDIR"] = old_tmpdir
            else:
                os.environ.pop("TMPDIR", None)

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["edit"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("pkg_config_name", "libedit")