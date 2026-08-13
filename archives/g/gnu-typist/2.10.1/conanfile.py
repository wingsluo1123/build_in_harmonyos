#!/usr/bin/env python3
"""Conan recipe for gnu-typist 2.10.1 — Autotools project with system ncurses."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os


class GnutypistConan(ConanFile):
    name = "gnu-typist"
    version = "2.10.1"
    description = "GNU Typist — a typing tutor"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/gtypist/"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        pass

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Cross-compilation: only add --build/--host for OHOS builds
        if self.settings.os == "OHOS":
            tc.configure_args.append("--build=aarch64-linux-gnu")
            tc.configure_args.append("--host=aarch64-linux-gnu")
        # Suppress int-conversion error from bundled getopt.c (uses 0 as NULL)
        tc.extra_cflags.append("-Wno-int-conversion")
        # Define gettext stubs for NLS-disabled builds (via -include to avoid
        # shell quoting issues with parentheses in -D flags)
        tc.extra_cflags.append("-include")
        tc.extra_cflags.append("_tools/gettext_stub.h")
        tc.configure_args.append("--disable-nls")
        # Detect system ncursesw via its config tool (portable, no hardcoded paths)
        import subprocess as _sp
        import shutil as _su
        _ncursesw6 = _su.which("ncursesw6-config") or \
                     _su.which("ncursesw6-config", path=os.environ.get("PATH","") + ":" +
                               "/usr/local/bin:/usr/bin:" +
                               os.environ.get("HOME","") + "/usr/local/bin")
        if _ncursesw6:
            try:
                _ncurses_cflags = _sp.check_output(
                    [_ncursesw6, "--cflags"], text=True
                ).strip()
                _ncurses_libs = _sp.check_output(
                    [_ncursesw6, "--libs"], text=True
                ).strip()
                # A stale ncursesw6-config may emit an -I path pointing at a
                # deleted staging prefix while --libs stays valid.  Keep only
                # include paths that actually exist (and the -D defines).
                _ncurses_keep = []
                for _tok in _ncurses_cflags.split():
                    if _tok.startswith("-I") and not os.path.isdir(_tok[2:]):
                        continue
                    _ncurses_keep.append(_tok)
                # If no include path survived, derive one from --libs' -L libdir
                # (same ncurses install tree: libdir/../include).
                if not any(_t.startswith("-I") for _t in _ncurses_keep):
                    for _tok in _ncurses_libs.split():
                        if _tok.startswith("-L"):
                            _inc_guess = os.path.normpath(
                                os.path.join(_tok[2:], "..", "include")
                            )
                            if os.path.isfile(
                                os.path.join(_inc_guess, "ncursesw", "ncurses.h")
                            ):
                                _ncurses_keep.append("-I" + _inc_guess)
                            break
                _ncurses_cflags = " ".join(_ncurses_keep)
                # CPPFLAGS for configure header checks (AC_CHECK_HEADERS uses CPPFLAGS)
                tc.configure_args.append("CPPFLAGS=" + _ncurses_cflags)
                # CFLAGS for compilation
                tc.extra_cflags.append(_ncurses_cflags)
                # LDFLAGS for linking
                tc.extra_ldflags.append(_ncurses_libs)
            except (_sp.CalledProcessError, FileNotFoundError):
                self.output.warning("ncursesw6-config found but failed to run")
        else:
            self.output.warning("ncursesw6-config not found in PATH. "
                                "ncursesw headers may be missing from compiler search path.")
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        import os as _os
        # Save full environment to restore after build (R33)
        _saved_environ = dict(_os.environ)
        try:
            # Inline mktemp fix for HMDFS: upstream configure uses mktemp -d
            # which fails on HMDFS (t=$(mktemp -p . confXXXXXX.tmp) fallback)
            from pathlib import Path as _Path
            _cf = _Path(self.source_folder) / "configure"
            if _cf.is_file():
                _txt = _cf.read_text(encoding="utf-8")
                _old = '  tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&'
                _new = '  tmp=`(umask 077 && t=$(mktemp -p . confXXXXXX.tmp) && rm -f "$t" && mkdir -p "$t" && echo "$t") 2>/dev/null` &&'
                if _old in _txt:
                    _cf.write_text(_txt.replace(_old, _new), encoding="utf-8")
            # [R33] PATH adjustments for OHOS platform limitations (E106/E079):
            #   - Prefix /bin: HMDFS GNU cat stdout permission issue (E106)
            #   - _tools/: help2man/makeinfo not available on OHOS (E079)
            _os.environ["PATH"] = "/bin:" + _saved_environ.get("PATH", "")
            # Create wrapper scripts for missing tools
            _os.makedirs("_tools", exist_ok=True)
            with open("_tools/help2man", "w") as f:
                f.write("#!/bin/sh\nexit 0\n")
            _os.chmod("_tools/help2man", 0o755)
            with open("_tools/makeinfo", "w") as f:
                f.write("#!/bin/sh\nexit 0\n")
            _os.chmod("_tools/makeinfo", 0o755)
            with open("_tools/gettext_stub.h", "w") as f:
                f.write("/* gettext stub for NLS-disabled builds */\n")
                f.write("#define gettext(x) (x)\n")
                f.write("#define _(x) (x)\n")
            _os.environ["PATH"] = _os.path.abspath("_tools") + ":" + _os.environ.get("PATH", "")
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j1"])
        finally:
            # R33: restore original environment after build
            _os.environ.clear()
            _os.environ.update(_saved_environ)

    def package(self):
        import os as _os
        _saved_path = _os.environ.get("PATH", "")
        try:
            # _tools/ created in build() — still on disk; add to PATH for install
            _tools_dir = _os.path.join(self.build_folder, "_tools")
            if _os.path.isdir(_tools_dir):
                _os.environ["PATH"] = _tools_dir + ":" + _saved_path
            autotools = Autotools(self)
            autotools.install()
        finally:
            _os.environ["PATH"] = _saved_path

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
