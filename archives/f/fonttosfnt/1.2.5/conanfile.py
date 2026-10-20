#!/usr/bin/env python3
"""Conan recipe — fonttosfnt 1.2.5 for OHOS (HarmonyOS PC).

fonttosfnt wraps a set of BDF (or PCF) bitmap fonts in an sfnt (TrueType /
OpenType) wrapper -- the `.otb` "OpenType bitmap font" form consumed by the X
server and by modern FreeType-based stacks. Upstream ships a full autotools
release tree (configure + Makefile.am + man/) and installs a single CLI,
`bin/fonttosfnt`, plus its man page -- no library and no headers. The package
is therefore declared `application` (R38/PF8) and carries a software-level
`commands.json`.

Dependency surface is exactly the three pkg-config modules named by
configure.ac:

    PKG_CHECK_MODULES(FONTTOSFNT, [xproto >= 7.0.33 freetype2 fontenc])

* `xproto`    -> conan `xorgproto/2025.1`  (X11 protocol headers; read.c
                 includes "X11/Xos.h")
* `freetype2` -> conan `freetype/2.14.3.2.1` (read.c drives FreeType's BDF
                 driver: FT_Open_Face / FT_Get_Font_Format / FT_BDF_H)
* `fontenc`   -> conan `libfontenc/1.1.7`  (read.c calls FontEncMapFind /
                 FontMapReverse to re-encode non-ISO10646 fonts)

`libfontenc/1.1.9` exists in the archive tree but is **not** published on the
ohpcd remote -- probed with `conan download --only-recipe libfontenc/1.1.9
-r=ohpcd`, which answers the remote's "not found" error (identical to the
answer for a bogus name/version), while 1.1.7 downloads fine. The requirement
is pinned to the newest published revision, 1.1.7 (R35/R36).

Upstream's shipped autoconf scripts predate HarmonyOS, so build() teaches them
about the OS before configure runs. Every edit is guarded by an "already
present" test, so the function is idempotent whether or not
`refresh-patch --auto` has materialised the same fixes as patches/:

* config.guess (timestamp 2024-07-27) does not know `uname -s = HarmonyOS`
  (E007/E072) and ends in "unable to guess system type". The edit adds a
  `*:HarmonyOS:*:*` arm to the `$UNAME_MACHINE:$UNAME_SYSTEM:...` dispatch that
  guesses `<machine>-unknown-linux-ohos`. This tarball's shipped config.sub
  already accepts that tuple (verified in place: `config.sub
  aarch64-unknown-linux-ohos` -> `aarch64-unknown-linux-ohos`, rc=0), so
  config.sub needs no edit. `--build`/`--host` was deliberately NOT used to
  bypass config.guess -- that would flip autoconf into cross mode and change
  the semantics of the AC_CHECK_FUNC / AC_CHECK_FUNCS / AC_CHECK_DECLS probes
  that decide config.h (setenv / vasprintf / va_copy).
* config.guess and configure create their scratch dirs with
  `umask 077 && mktemp -d`; a 700 directory on HMDFS cannot be written into, so
  config.guess dies with "can't create .../dummy.c: Permission denied" and
  configure then reports "cannot guess build type; you must specify one"
  (E011/E114). umask is relaxed to 022, keeping the real temp-dir creation.
  config.status inherits the configure block verbatim at configure time, hence
  the edit must be on disk before configure runs.

No platform preprocessor macro is introduced anywhere (R8 / PF5) -- both edits
recognise the OS by its uname name only.
"""
import os
import re

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import (
    Autotools,
    AutotoolsDeps,
    AutotoolsToolchain,
    PkgConfigDeps,
)
from conan.tools.layout import basic_layout

HARMONY_CASE = (
    "    *:HarmonyOS:*:*)\n"
    "\tcase $UNAME_MACHINE in\n"
    "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
    "\t    armv7*|armv8*) MACHINE=arm ;;\n"
    "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
    "\t    i?86)          MACHINE=i686 ;;\n"
    "\t    *)             MACHINE=$UNAME_MACHINE ;;\n"
    "\tesac\n"
    "\tGUESS=$MACHINE-unknown-linux-ohos\n"
    "\t;;\n"
)

GUESS_DISPATCH = ("case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:"
                  "$UNAME_VERSION in\n")


def _patch_autotools_scripts(root):
    """Teach the shipped autotools scripts about HarmonyOS and HMDFS umask.

    Deliberately free of injected platform macros: PF5 blocks a platform
    preprocessor define added through conanfile.py edits, and none of the
    edits below needs one -- the OS is recognised by its uname name rather
    than by a C macro.
    """
    edited = []

    cg_path = os.path.join(root, "config.guess")
    if os.path.exists(cg_path):
        with open(cg_path, "r", encoding="utf-8",
                  errors="surrogateescape") as f:
            cg = f.read()
        cg_start = cg

        if "*:HarmonyOS:*:*" not in cg:
            idx = cg.find(GUESS_DISPATCH)
            if idx >= 0:
                idx += len(GUESS_DISPATCH)
                cg = cg[:idx] + HARMONY_CASE + cg[idx:]
                edited.append("config.guess:HarmonyOS-case")

        if "umask 077" in cg:
            cg = cg.replace("umask 077", "umask 022")
            edited.append("config.guess:umask022")

        if cg != cg_start:
            with open(cg_path, "w", encoding="utf-8",
                      errors="surrogateescape") as f:
                f.write(cg)

    cfg_path = os.path.join(root, "configure")
    if os.path.exists(cfg_path):
        with open(cfg_path, "r", encoding="utf-8",
                  errors="surrogateescape") as f:
            cfg = f.read()
        cfg_start = cfg

        if "umask 077" in cfg:
            cfg = cfg.replace("umask 077", "umask 022")
            edited.append("configure:umask022")

        if cfg != cfg_start:
            # config.status inherits this block verbatim at configure time, so
            # the edit only counts once it is on disk -- recording it without
            # writing back would leave config.status still creating a 700 dir.
            with open(cfg_path, "w", encoding="utf-8",
                      errors="surrogateescape") as f:
                f.write(cfg)

    return edited


class FonttosfntConan(ConanFile):
    name = "fonttosfnt"
    version = "1.2.5"
    description = ("X.Org tool that wraps BDF/PCF bitmap fonts in an sfnt "
                   "(TrueType/OpenType) .otb wrapper")
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/app/fonttosfnt"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"  # recipe repo

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("xorgproto/2025.1")
        self.requires("freetype/2.14.3.2.1")
        # Newest libfontenc revision actually published on ohpcd (1.1.9 is
        # archived in-tree but absent from the remote -- see module docstring).
        self.requires("libfontenc/1.1.7")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # configure.ac uses PKG_CHECK_MODULES, so the pkg-config descriptors
        # (xproto.pc / freetype2.pc / fontenc.pc) must be present in
        # PKG_CONFIG_PATH; AutotoolsDeps additionally contributes the
        # CPPFLAGS/LDFLAGS of the whole graph to the autotools environment.
        PkgConfigDeps(self).generate()
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # R1: --prefix only; upstream configure.ac has no project switch.
        tc.generate()

        # Conan-cached shared libraries are not on the OHOS loader's default
        # search path. AutotoolsDeps only contributes -I/-L/-l, so autoconf's
        # very first sanity probe (which links conftest.c against the whole
        # graph) produces a binary that cannot start:
        #     Error loading shared library libfontenc.so.1: (needed by ./conftest)
        #     Error loading shared library libfreetype.so.6: (needed by ./conftest)
        #     configure: error: cannot run C compiled programs.
        # (configure then also flips into cross-compiling mode and would skip
        # the AC_RUN_IFELSE probes that decide config.h). Prepending the
        # dependency libdirs to LD_LIBRARY_PATH in the conanbuild environment
        # is the fix recorded for this exact signature -- same mitigation as
        # xdriinfo/1.0.8 (and aaphoto/0.45, dirb/2.22); the build stays native
        # (no --build/--host), so the triplet still comes from the patched
        # config.guess.
        env = Environment()
        for dep in self.dependencies.host.values():
            for libdir in dep.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dep.package_folder, libdir)
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self, scope="build").save_script("conanbuild_runpath")

    def build(self):
        apply_conandata_patches(self)

        edited = _patch_autotools_scripts(self.source_folder)
        if edited:
            self.output.info(f"autotools script patches applied: {edited}")

        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        # Upstream registers no automated tests at all (no TESTS entry in
        # Makefile.am / man/Makefile.am, no check_PROGRAMS, no test directory
        # -- see notes.md and test_package/MANIFEST.yml for the four-lens
        # inventory). `make check` is still executed so the registration is
        # observed rather than assumed: automake recurses into man/ and prints
        # "Nothing to be done for 'check'", exit code 0. The real behavioural
        # coverage is the consumer program in test_package/.
        autotools.make(target="check")

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
        # fonttosfnt is a command line tool: bin/fonttosfnt plus the
        # fonttosfnt.1 man page, no headers and no libraries.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
