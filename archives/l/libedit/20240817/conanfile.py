#!/usr/bin/env python3
"""Conan recipe for libedit 20240817 — Autotools project.

libedit is a line editing library for interactive command-line programs.
It provides the BSD-licensed editline and readline compatible API.

Fixes for OHOS/HMDFS:
- TMPDIR: set to writable location (/tmp is erofs read-only)
- config.status: umask 077 creates mode 0700 dirs that HMDFS can't write to;
  the build() method patches configure to use umask 022 before running it.
- ncurses: use system libncursesw.a (conan ncurses/6.4 configure fails on /tmp erofs)
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibeditConan(ConanFile):
    name = "libedit"
    version = "20240817"
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
        # System ncurses include path
        ncurses_inc = os.environ.get("NCURSES_INCLUDE",
            "/storage/Users/currentUser/tmp/test-install-ncurses-6.4/include")
        ncurses_lib = os.environ.get("NCURSES_PREFIX",
            "/storage/Users/currentUser/usr/local")
        tc.extra_cflags.append(f"-I{ncurses_inc}")
        tc.extra_ldflags.append(f"-L{ncurses_lib}/lib")
        tc.generate()

    def build(self):
        # ── Fix 1: ncurses symlink ──
        ncurses_lib = os.environ.get("NCURSES_PREFIX",
            "/storage/Users/currentUser/usr/local")
        libncurses = os.path.join(ncurses_lib, "lib", "libncurses.a")
        libncursesw = os.path.join(ncurses_lib, "lib", "libncursesw.a")
        if not os.path.exists(libncurses) and os.path.exists(libncursesw):
            os.symlink("libncursesw.a", libncurses)
            self.output.info(f"Created symlink: libncurses.a -> libncursesw.a")

        # ── Fix 2: TMPDIR for /tmp erofs ──
        old_tmpdir = os.environ.get("TMPDIR")
        writable_tmp = "/storage/Users/currentUser/.conan2/tmp"
        os.environ["TMPDIR"] = writable_tmp

        # ── Fix 3: patch configure to use umask 022 instead of 077 ──
        # On HMDFS, umask 077 creates mode 0700 dirs that can't be written to.
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure_path):
            with open(configure_path) as f:
                content = f.read()
            # Change umask 077 to umask 022 in the temp dir creation section
            original = 'umask 077 && mktemp -d "./confXXXXXX"'
            replacement = 'umask 022 && mktemp -d "./confXXXXXX"'
            if original in content:
                content = content.replace(original, replacement)
                with open(configure_path, "w") as f:
                    f.write(content)
                self.output.info("Patched configure: umask 077 -> 022 for temp dir")
            else:
                self.output.warning("umask 077 pattern not found in configure")

        # ── Fix 4: termcap function declarations for OHOS ncurses ──
        # terminal.c declares tgetent/tgoto/tgetflag/tgetnum/tgetstr/tputs
        # only for __sun; OHOS ncurses has them in the library but not declared
        # in the headers. We add __OHOS__ to the same guard.
        terminal_c = os.path.join(self.source_folder, "src", "terminal.c")
        if os.path.exists(terminal_c):
            with open(terminal_c) as f:
                content = f.read()
            old_guard = '#if defined(__sun)'
            new_guard = '#if defined(__sun) || defined(__OHOS__)'
            if old_guard in content:
                content = content.replace(old_guard, new_guard)
                with open(terminal_c, "w") as f:
                    f.write(content)
                self.output.info("Patched terminal.c: added __OHOS__ to termcap decl guard")
            else:
                self.output.warning("__sun guard not found in terminal.c, checking content...")
                # Check if the guard is already there
                if '__OHOS__' in content:
                    self.output.info("__OHOS__ guard already present in terminal.c")
                else:
                    # Try to find the actual guard pattern
                    for line in content.split('\n'):
                        if 'tgetent' in line and 'extern' in line:
                            self.output.info(f"Found tgetent decl: {line.strip()}")

        try:
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
