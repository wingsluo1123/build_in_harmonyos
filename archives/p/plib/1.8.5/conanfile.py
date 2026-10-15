#!/usr/bin/env python3
"""Conan recipe — plib 1.8.5 (Autotools, C++).

PLIB is a portable game programming library (utility/math/scene-graph/net/
joystick/PSL modules).  The OpenGL-dependent modules (fnt, pui->plibpu,
puAux->plibpuaux, ssg, ssgAux), the audio module (sl->plibsl/plibsm) and the
pw portability module (whose only *nix backend needs X11) are disabled on
OHOS, which has no GL/audio/X11 toolchain requirement on the consumer side;
the preserved feature set is the core modules:
  ul (utility), sg (3D math), psl (programmable shading language front-end),
  net (buffered TCP), js (joystick).

Upstream: http://plib.sourceforge.net (sourceforge project files for 1.8.5 are
gone; the pristine upstream tarball is taken from the Debian pool, see
conandata.yml).
"""
import glob
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class PlibConan(ConanFile):
    name = "plib"
    version = "1.8.5"
    description = "PLIB - a collection of portable game programming libraries"
    license = "LGPL-2.0-or-later"
    homepage = "http://plib.sourceforge.net"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("plib", "game", "math", "utility", "autotools")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def build_requirements(self):
        # The copies of config.guess/config.sub shipped by this toolchain
        # package are modern GNU ones (aarch64 aware). build() installs them in
        # place of plib's 2006-era helpers instead of carrying ~3.8k lines of
        # vendored scripts in the recipe (E007; see notes.md).
        self.tool_requires("automake/1.18")

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "plib is supported only on Linux/OHOS, not %s" % self.settings.os
            )

    def layout(self):
        # plib's autotools does not support out-of-source (VPATH) builds.
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            # OpenGL / GLUT dependent modules (no GL on OHOS consumer side)
            "--disable-fnt",     # FNT  -> libplibfnt
            "--disable-pui",     # PUI  -> libplibpu (OpenGL)
            "--disable-puaux",   # puAux-> libplibpuaux (OpenGL)
            "--disable-ssg",     # SSG  -> libplibssg (OpenGL)
            "--disable-ssgaux",  # ssgAux -> libplibssgaux (OpenGL)
            # audio module (ALSA/OSS)
            "--disable-sl",      # SL/SM -> libplibsl/libplibsm
            # portability module: its only *nix backend is X11
            # (pwX11.cxx -> X11/Xlib.h); OHOS has no X11.
            "--disable-pw",      # PW -> libplibpw
        ])
        tc.generate()

    @staticmethod
    def _patch_configure_umask(configure_path):
        """Drop the `umask 077 &&` temp-dir wrappers (HMDFS setgid E118).

        HMDFS forces setgid on directories, so `umask 077 && mktemp -d`
        yields a drwx--S--- dir that is not writable even by its owner;
        config.status then dies with `./confXXXXXX/out: Permission denied`
        and no Makefile is created (E118). Plain string replacement so it
        applies to any autoconf vintage.
        """
        try:
            with open(configure_path, "r", encoding="utf-8", errors="replace") as handle:
                content = handle.read()
        except OSError:
            return
        content = content.replace("umask 077 && ", "")
        with open(configure_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)

    # HarmonyOS branch for config.guess — the same edit that
    # scripts/patch-autotools-ohos.pl makes (E007).  The device reports
    # `uname -s` = HarmonyOS; matching it here resolves the triplet *before*
    # config.guess's libc compile probe, which HMDFS rejects (E011/E118).
    _HARMONYOS_CASE = (
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

    def _install_config_helpers(self):
        """Overwrite plib's 2006-era config.guess/config.sub with the modern
        GNU helpers shipped by automake (E007) and teach config.guess about
        HarmonyOS.  Iron-rule #0: the triplet stays aarch64-unknown-linux-ohos
        through config.guess, never via --build/--host."""
        base = self.dependencies.build["automake"].package_folder
        for helper in ("config.guess", "config.sub"):
            matches = glob.glob(os.path.join(base, "**", helper), recursive=True)
            if not matches:
                raise ConanException(
                    "automake package does not ship %s" % helper)
            dst = os.path.join(self.source_folder, helper)
            shutil.copy2(sorted(matches, key=len)[0], dst)
            os.chmod(dst, 0o755)
        self._add_harmonyos_branch(os.path.join(self.source_folder, "config.guess"))
        config_sub = os.path.join(self.source_folder, "config.sub")
        with open(config_sub, "r", encoding="utf-8", errors="replace") as handle:
            if "linux-ohos" not in handle.read():
                raise ConanException(
                    "automake config.sub has no linux-ohos support")

    def _add_harmonyos_branch(self, guess_path):
        with open(guess_path, "r", encoding="utf-8", errors="replace") as handle:
            content = handle.read()
        if "HarmonyOS" in content:
            return
        # Same anchor as patch-autotools-ohos.pl: the NetBSD case, present in
        # every modern GNU config.guess.
        content, count = re.subn(
            r"(^[ \t]+\*:NetBSD:\*:\*\)[ \t]*\n)",
            self._HARMONYOS_CASE + r"\1",
            content, count=1, flags=re.M,
        )
        if count == 0:
            raise ConanException(
                "config.guess: NetBSD anchor not found; cannot add HarmonyOS branch")
        with open(guess_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)

    def build(self):
        apply_conandata_patches(self)
        self._install_config_helpers()
        self._patch_configure_umask(os.path.join(self.source_folder, "configure"))
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # PLIB is a set of separate static libraries (non-GL/non-audio set).
        self.cpp_info.libs = [
            "plibul", "plibsg", "plibpsl", "plibnet", "plibjs",
        ]
