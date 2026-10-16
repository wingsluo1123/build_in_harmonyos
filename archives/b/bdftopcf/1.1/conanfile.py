#!/usr/bin/env python3
"""Conan recipe — bdftopcf 1.1 for OHOS (HarmonyOS PC).

bdftopcf is the X.Org font compiler that turns BDF (Bitmap Distribution
Format) into PCF (Portable Compiled Format) for the X server and font
server. Upstream ships a plain autotools tree (configure + Makefile.am,
the official X.Org release path) and builds a single `bin/bdftopcf` CLI --
no library and no headers installed.

Dependency surface is headers only. bdftopcf compiles against
`X11/X.h`, `X11/Xproto.h`, `X11/Xos.h`, `X11/Xfuncproto.h`,
`X11/Xfuncs.h`, `X11/Xdefs.h` and `X11/fonts/{fontstruct,FSproto}.h`;
every one of those lives in the conan `xorgproto` package (verified by
searching the package include tree on this device), and the program links
no X library at all -- configure.ac declares no PKG_CHECK_MODULES /
AC_CHECK_LIB and Makefile.am's link line carries only $(CWARNFLAGS).
So `xorgproto/2025.1` is the whole graph.

Upstream configure does host-style discovery that cannot succeed on OHOS,
so build() teaches the shipped shell scripts about the operating system
before configure runs. No platform preprocessor macro is injected
anywhere (R8 / PF5) -- the edits only recognise the OS by its uname name:

* config.guess (2017-08-08) does not know `uname -s = HarmonyOS`
  (E007/E072). The patch adds a `*:HarmonyOS:*:*` case that echoes
  `aarch64-unknown-linux-ohos`.  This tarball's config.guess predates the
  `GUESS=` variable idiom: every branch here does `echo <tuple>; exit ;;`
  directly, so the branch must echo + exit rather than assign GUESS.
* config.sub (2017-04-02) must accept that tuple. Two places, each with
  its own guard: the KERNEL-OS list up top (`linux-ohos*`, which makes
  basic_machine collapse to `aarch64-unknown` instead of the unrecognized
  `aarch64-unknown-linux`) and the "basic system types" list further down
  (`-linux-ohos*`, which keeps the later `-linux*)` alias branch from
  rewriting os into `-linux-gnu-ohos`).
* config.status is created from configure's template with
  `umask 077 && mktemp -d "./confXXXXXX"`, which yields a 700 directory
  HMDFS refuses to write into (E110/E112), so umask is relaxed to 022 and
  mktemp replaced with mkdir.

`--build`/`--host` was deliberately NOT used to bypass config.guess:
telling autoconf this is a cross build skips AC_RUN_IFELSE checks and
produces a wrong config.h.

Every edit is guarded by an "already present" test, so the function is
idempotent whether or not `refresh-patch --auto` has materialised the
same fixes as patches/.
"""
import os
import re

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _patch_autotools_scripts(root):
    """Teach config.guess/config.sub about HarmonyOS and unblock HMDFS temp dirs.

    Deliberately free of injected platform macros: PF5 blocks a platform
    preprocessor define added through conanfile.py replace() calls, and none
    of the edits below needs one -- the OS is recognised by its uname name
    rather than by a C macro.
    """
    edited = []

    for dirpath, _, files in os.walk(root):
        if "config.guess" not in files or "config.sub" not in files:
            continue

        # --- config.guess: recognize uname -s = HarmonyOS ---
        cg_path = os.path.join(dirpath, "config.guess")
        with open(cg_path, "r", encoding="utf-8", errors="surrogateescape") as f:
            cg = f.read()
        cg_start = cg

        if "*:HarmonyOS:*:*" not in cg:
            # config.guess timestamp 2017-08-08 has no GUESS= variable: each
            # branch echoes the tuple and exits.
            block = (
                "    *:HarmonyOS:*:*)\n"
                "\tcase \"$UNAME_MACHINE\" in\n"
                "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
                "\t    armv7*|armv8*) MACHINE=arm ;;\n"
                "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
                "\t    i?86)         MACHINE=i686 ;;\n"
                "\t    *)            MACHINE=\"$UNAME_MACHINE\" ;;\n"
                "\tesac\n"
                "\techo ${MACHINE}-unknown-linux-ohos\n"
                "\texit ;;\n\n"
            )
            cg, n = re.subn(
                r"(^[ \t]+\*:NetBSD:\*\:\*\)[ \t]*\n)",
                lambda m: block + m.group(1),
                cg,
                count=1,
                flags=re.MULTILINE,
            )
            if n:
                edited.append("config.guess:HarmonyOS-case")

        # HMDFS: a 700 scratch dir cannot be written into (E110).
        cg = cg.replace(
            '(umask 077 && mktemp -d "$TMPDIR/cgXXXXXX") 2>/dev/null',
            '(umask 022 && mkdir "$TMPDIR/cgXXXXXX.$$" && '
            'echo "$TMPDIR/cgXXXXXX.$$") 2>/dev/null',
        )
        cg = cg.replace("(umask 077 &&", "(umask 022 &&")
        if cg != cg_start:
            if "(umask 022 &&" in cg and "umask 022" not in cg_start:
                edited.append("config.guess:umask022")
            with open(cg_path, "w", encoding="utf-8", errors="surrogateescape") as f:
                f.write(cg)

        # --- config.sub: make aarch64-unknown-linux-ohos a valid tuple ---
        cs_path = os.path.join(dirpath, "config.sub")
        with open(cs_path, "r", encoding="utf-8", errors="surrogateescape") as f:
            cs = f.read()
        cs_start = cs

        # KERNEL-OS list at the top of config.sub.
        if "linux-ohos*" not in cs:
            old = ("  nto-qnx* | linux-gnu* | linux-android* | linux-dietlibc "
                   "| linux-newlib* | \\")
            new = ("  nto-qnx* | linux-gnu* | linux-android* | linux-ohos* "
                   "| linux-dietlibc | linux-newlib* | \\")
            if old in cs:
                cs = cs.replace(old, new, 1)
                edited.append("config.sub:kernel-os-list")

        # "basic system types" list further down: without it the later
        # `-linux*)` alias branch rewrites os into `-linux-gnu-ohos`.
        if "-linux-ohos*" not in cs:
            old = ("\t      | -midipix* | -mingw32* | -mingw64* | -linux-gnu* "
                   "| -linux-android* \\")
            if old in cs:
                cs = cs.replace(old, old + "\n\t      | -linux-ohos* \\", 1)
                edited.append("config.sub:basic-os-list")

        if cs != cs_start:
            with open(cs_path, "w", encoding="utf-8", errors="surrogateescape") as f:
                f.write(cs)

    # --- configure: config.status scratch dir must be 755, not 700 (E112) ---
    cfg_path = os.path.join(root, "configure")
    if os.path.exists(cfg_path):
        with open(cfg_path, "r", encoding="utf-8", errors="surrogateescape") as f:
            cfg = f.read()
        cfg_start = cfg
        cfg = cfg.replace(
            '  tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&\n'
            '  test -d "$tmp"',
            '  tmp=./conf$$-$RANDOM\n'
            '  (umask 022 && mkdir "$tmp" && chmod 755 "$tmp")',
        )
        cfg = cfg.replace(
            '(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null',
            '(umask 022 && mkdir ./conf$$-$RANDOM && chmod 755 ./conf$$-$RANDOM)',
        )
        cfg = cfg.replace("(umask 077 &&", "(umask 022 &&")
        if cfg != cfg_start:
            # config.status inherits this block verbatim at configure time, so
            # the edit only counts once it is on disk -- recording it without
            # writing back would leave config.status still creating a 700 dir.
            with open(cfg_path, "w", encoding="utf-8", errors="surrogateescape") as f:
                f.write(cfg)
            edited.append("configure:umask022")

    return edited


class BdftopcfConan(ConanFile):
    name = "bdftopcf"
    version = "1.1"
    description = "X.Org BDF to PCF font compiler for the X server and font server"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/app/bdftopcf"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"  # recipe repo

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # Headers only: bdftopcf links no X library (configure.ac declares no
        # PKG_CHECK_MODULES / AC_CHECK_LIB; Makefile.am's link line is
        # $(CWARNFLAGS) only). All eight X11 headers it includes live in the
        # conan xorgproto package -- verified by find on this device.
        self.requires("xorgproto/2025.1")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # AutotoolsDeps contributes the xorgproto -I flags; xorgproto's
        # cpp_info.libs is empty so no -l lands on the link line.
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        # R1: --prefix only; upstream configure.ac has no project switch.
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        edited = _patch_autotools_scripts(self.source_folder)
        if edited:
            self.output.info(f"autotools script patches applied: {edited}")

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        # bdftopcf is a command line tool: bin/bdftopcf plus the bdftopcf.1
        # man page, no headers and no libraries.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
