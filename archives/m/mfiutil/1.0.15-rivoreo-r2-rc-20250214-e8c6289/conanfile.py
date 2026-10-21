#!/usr/bin/env python3
"""Conan recipe for mfiutil 1.0.15-rivoreo-r2-rc-20250214-e8c6289 — LSI MegaRAID SAS controller management CLI.

mfiutil is a lightweight, portable utility that provides basic management
functionality for LSI MegaRAID SAS controllers (adapter/firmware queries,
BBU properties, patrol read, foreign-config import, firmware flashing).
It was initially ported from FreeBSD's usr.sbin/mfiutil and is maintained
by the Rivoreo project; on Linux it drives the megaraid_sas(4) driver
through the /dev/megaraid_sas_ioctl character node. It is a plain-C
program (13 translation units) built by a hand-written Makefile.

OHOS adaptive build:
  - CC comes from Conan conf tools.build:compiler_executables (R33), never
    a bare shell var or hardcoded path. The upstream Makefile hardcodes
    `CC := gcc`, but a command-line assignment overrides it (GNU make
    semantics), so no Makefile patch is needed.
  - CFLAGS stay at the Makefile defaults (-std=gnu99 -Wall -Wno-unused-value
    -Os -I include); the Makefile also appends $(CPPFLAGS) for BSD make.
  - No third-party dependency: libc only. The Linux code path is selected
    by the compiler's predefined macros (__linux__), the same way
    Debian/Kali build it; the FreeBSD/Solaris/Darwin-only blocks
    (HAVE_MFI_DRIVER, __SVR4, AvailabilityMacros.h) stay compiled out.
  - Install uses the upstream `install` target with DESTDIR + PREFIX=/usr.

Upstream tests: mfiutil has NO test suite — the repository ships no tests/
directory and the Makefile has no check/test target (only default, clean,
install). See test_package/MANIFEST.yml for the full audit.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MfiutilConan(ConanFile):
    name = "mfiutil"
    version = "1.0.15-rivoreo-r2-rc-20250214-e8c6289"
    package_type = "application"

    description = "Management utility for LSI MegaRAID SAS controllers (portable port of FreeBSD mfiutil)"
    license = "BSD-2-Clause AND MIT"
    homepage = "https://rivoreo.one/?id=Project:mfiutil"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("raid", "megaraid", "lsi", "storage", "cli", "utility")

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: the check must accept Linux AND OHOS, never `== "Linux"` only.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} only supports os=Linux/OHOS, got {self.settings.os}")

    def source(self):
        # Rivoreo Gitiles archives are flat (no top-level directory),
        # hence strip_root=False.
        get(self, **self.conan_data["sources"], strip_root=False)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, not shell env vars.
        # Profile sets tools.build:compiler_executables to the OHOS clang.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        # If the configured path exists, use it directly; otherwise fall back
        # to basename lookup via shutil.which (portable, no hardcoded paths).
        if os.path.isfile(cc):
            cc_bin = cc
        else:
            cc_bin = shutil.which(os.path.basename(cc)) or cc

        # Verify the compiler target triple is OHOS aarch64.
        triple = self._target_triple(cc_bin)
        if triple and "ohos" not in triple:
            self.output.warn(f"compiler triple '{triple}' is not an OHOS target")
        self.output.info(f"using CC: {cc_bin} (triple: {triple or 'unknown'})")

        # Command-line assignment overrides the Makefile's `CC := gcc`.
        # CFLAGS/LDFLAGS stay at the Makefile defaults (nothing passed).
        self.run(f'make CC="{cc_bin}" -j1', cwd=self.source_folder)

    @staticmethod
    def _target_triple(cc):
        import subprocess
        for flag in ("-print-target-triple", "-dumpmachine"):
            try:
                out = subprocess.run(
                    [cc, flag], capture_output=True, text=True, timeout=10)
                if out.returncode == 0 and out.stdout.strip():
                    return out.stdout.strip()
            except Exception:
                continue
        return ""

    def package(self):
        # Upstream `install` target honours DESTDIR/PREFIX/SBINDIR/MANDIR;
        # the man page lands in share/man/man8. PREFIX=/usr keeps the
        # packaged layout Conan-idiomatic (no /usr/local prefix).
        self.run(f'make install DESTDIR="{self.package_folder}" PREFIX=/usr',
                 cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.bindirs = ["usr/sbin"]
