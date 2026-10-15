#!/usr/bin/env python3
"""Conan recipe — appres 1.0.7 for OHOS (HarmonyOS PC).

appres is the X.Org application resource viewer: a small X11 client that
prints the resource database of running X clients. Upstream ships both an
autotools tree (configure + Makefile.am, the official X.Org release path) and
a meson.build; this recipe builds the autotools path, which is the one the
release tarball is validated against and the one CI can reproduce (autotools
is present on every worker, meson is not).

Upstream configure does host-style discovery that cannot succeed on OHOS, so
build() patches the three things that break, in place, before configure runs.
No platform preprocessor macro is injected anywhere (R8 / PF5) -- the patches
only teach the shipped shell scripts about the operating system name.

* config.guess / config.sub do not know `uname -s = HarmonyOS` (E007/E072).
  The patch adds a `*:HarmonyOS:*:*` case emitting
  aarch64-unknown-linux-ohos, plus the matching ohos-linux triplet mapping and
  the two OS/kernel whitelist entries. Passing --build/--host instead would
  make autoconf treat this as a cross build and skip AC_RUN_IFELSE checks,
  yielding a wrong config.h, so the scripts are patched rather than bypassed.
* config.sub's kernel-OS whitelist needs `linux-ohos*` added explicitly: the
  triplet patch above already writes the string `linux-ohos` elsewhere, so a
  naive "already present" guard skips this edit and configure dies with
  "Kernel `linux' not known to work with OS `ohos'".
* config.status creates its scratch dir with `umask 077 && mktemp -d`, which
  yields a 700 directory HMDFS refuses to write into (E110/E112
  Permission denied on ./confXXXXXX/subs1.awk). The umask is relaxed to 022
  and mktemp replaced with mkdir, so the scratch dir is created 755.

pkg-config note: upstream requires `x11 xt xproto >= 7.0.17`. The conan
xorgproto package only declares pkg_config_name=xorgproto, but xorgproto is
the project that *provides* xproto -- a real xorgproto install ships xproto.pc
too -- so generate() aliases it, which also makes the Requires: chains
generated for x11.pc/xt.pc resolve.
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
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


def _patch_autotools_scripts(root):
    """Teach config.guess/config.sub about HarmonyOS and unblock HMDFS temp dirs.

    Deliberately free of injected platform macros: PF5 blocks a platform
    preprocessor define added through conanfile.py replace() calls, and none
    of the edits below needs one -- the OS is recognised by its uname name
    rather than by a C macro.
    """
    edited = []

    # --- config.guess: recognize uname -s = HarmonyOS ---
    for dirpath, _, files in os.walk(root):
        if "config.guess" not in files or "config.sub" not in files:
            continue

        cg_path = os.path.join(dirpath, "config.guess")
        with open(cg_path, "r", encoding="utf-8", errors="surrogateescape") as f:
            cg = f.read()

        if "HarmonyOS" not in cg:
            block = (
                "    *:HarmonyOS:*:*)\n"
                "\tcase \"$UNAME_MACHINE\" in\n"
                "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
                "\t    armv7*|armv8*) MACHINE=arm ;;\n"
                "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
                "\t    i?86)         MACHINE=i686 ;;\n"
                "\t    *)            MACHINE=\"$UNAME_MACHINE\" ;;\n"
                "\tesac\n"
                "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
                "\t;;\n\n"
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
        orig = cg
        cg = cg.replace(
            '(umask 077 && mktemp -d "$TMPDIR/cgXXXXXX") 2>/dev/null',
            '(umask 022 && mkdir "$TMPDIR/cgXXXXXX.$$" && '
            'echo "$TMPDIR/cgXXXXXX.$$") 2>/dev/null',
        )
        cg = cg.replace("(umask 077 &&", "(umask 022 &&")
        if cg != orig:
            edited.append("config.guess:umask022")

        with open(cg_path, "w", encoding="utf-8", errors="surrogateescape") as f:
            f.write(cg)

        # --- config.sub: triplet + two whitelists ---
        cs_path = os.path.join(dirpath, "config.sub")
        with open(cs_path, "r", encoding="utf-8", errors="surrogateescape") as f:
            cs = f.read()

        if "ohos-linux" not in cs:
            cs, n = re.subn(
                r"^(\s*android-linux\)\s*\n)"
                r"((\s*)basic_machine=\$field1-unknown\s*\n)"
                r"((\s*)basic_os=linux-android\s*\n)"
                r"(\s*;;\s*\n)",
                lambda m: (
                    m.group(1)
                    + m.group(2)
                    + m.group(4)
                    + m.group(6)
                    + "\tohos-linux)\n"
                    + m.group(3)
                    + "basic_machine=$field1-unknown\n"
                    + m.group(5)
                    + "basic_os=linux-ohos\n"
                    + m.group(6)
                ),
                cs,
                count=1,
                flags=re.MULTILINE,
            )
            if n:
                edited.append("config.sub:ohos-linux-triplet")

        if not re.search(r"gnu\*\s*\|\s*android\*\s*\|\s*ohos\*", cs):
            cs, n = re.subn(r"(gnu\*\s*\|\s*android\*)", r"\1 | ohos*", cs, count=1)
            if n:
                edited.append("config.sub:os-whitelist")

        # The kernel-OS whitelist must be edited on its own: the triplet patch
        # above already introduced the substring `linux-ohos`, so testing for
        # that substring would wrongly report this entry as present.
        if "linux-gnu* | linux-dietlibc* | linux-ohos*" not in cs:
            cs, n = re.subn(
                r"(linux-gnu\* \| linux-dietlibc\*)",
                r"\1 | linux-ohos*",
                cs,
                count=1,
            )
            if n:
                edited.append("config.sub:kernel-whitelist")

        with open(cs_path, "w", encoding="utf-8", errors="surrogateescape") as f:
            f.write(cs)

    # --- configure: config.status scratch dir must be 755, not 700 (E112) ---
    cfg_path = os.path.join(root, "configure")
    if os.path.exists(cfg_path):
        with open(cfg_path, "r", encoding="utf-8", errors="surrogateescape") as f:
            cfg = f.read()
        orig = cfg
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
        if cfg != orig:
            # config.status inherits this block verbatim at configure time, so
            # the edit only counts once it is on disk -- recording it without
            # writing back left configure untouched and config.status still
            # creating a 700 dir HMDFS refuses (E112 Permission denied).
            with open(cfg_path, "w", encoding="utf-8", errors="surrogateescape") as f:
                f.write(cfg)
            edited.append("configure:umask022")

    return edited


class AppresConan(ConanFile):
    name = "appres"
    version = "1.0.7"
    description = "X.Org application resource viewer (X11 client)"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/app/appres"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"  # recipe repo

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def requirements(self):
        # libxt/1.3.1 itself requires libx11/1.8.13: pairing it with
        # libx11/6.4.0 makes the graph unsolvable, so 1.8.13 is the version
        # that actually resolves (conan graph info rc=0, verified).
        self.requires("libx11/1.8.13")
        self.requires("libxt/1.3.1")
        # Upstream configure.ac asks for `xproto >= 7.0.17`.
        self.requires("xorgproto/2025.1")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # xorgproto is the project that provides the xproto headers; upstream
        # configure.ac asks pkg-config for `xproto`, so alias the generated
        # .pc name (the Requires: chains of x11.pc/xt.pc follow the same
        # property, so the whole graph stays consistent).
        self.dependencies["xorgproto"].cpp_info.set_property(
            "pkg_config_name", "xproto"
        )
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
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
        # appres is a command line tool: it installs bin/appres and the
        # appres.1 man page, no headers and no libraries.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
