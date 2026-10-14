#!/usr/bin/env python3
"""Conan recipe for osdmixer 0.9 — OSD audio-volume monitor (CLI tool).

Upstream: osdmixer-0.9.tar.gz via the FreeBSD ports audio/osdmixer distfile
(PORTVERSION=0.9, MASTER_SITES=http://bsd-geek.de/FreeBSD/distfiles/).
The 2269-byte tarball holds exactly two files: a hand-written Makefile and
main.c (Peter Kupietz). The binary polls OSS /dev/mixer
(SOUND_MIXER_READ_VOLUME/PCM) in a helper thread and shows Master/PCM
percentage bars through libxosd (xosd.h).

Build system: hand-written Makefile, no configure, no install prefix logic.
Upstream `make` is a single cc line driven by `xosd-config --libs --cflags`;
this recipe instead passes CC/XOSD explicitly from the Conan dependency
graph (R33, hermetic: no xosd-config script lookup on PATH). Upstream
`make install` uses `install -Dm 0755 ... $(DESTDIR)/usr/bin` (playumidi
lesson: OHOS has no install(1) with -D), so package() copies the built
binary with Conan `copy` and never calls `make install`.

Upstream ships no test suite (see test_package/MANIFEST.yml audit).
"""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class OsdmixerConan(ConanFile):
    name = "osdmixer"
    version = "0.9"
    description = "Displays audio volume with an OSD (OSS mixer monitor using libxosd)"
    license = "Unknown"  # upstream tarball carries no LICENSE file or license header; FreeBSD port marks license "not specified in port" (see notes.md)
    homepage = "https://www.freshports.org/audio/osdmixer"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("osd", "mixer", "volume", "xosd", "oss", "cli")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "osdmixer/0.9 is adapted for Linux and OHOS, not %s" % self.settings.os
            )

    def requirements(self):
        # W0/R36: single runtime dependency. libxosd/2.2.14 is already
        # adapted in-tree (archives/l/libxosd) and pulls the X11 stack
        # (libx11/libxext/libxinerama/xorgproto) transitively.
        self.requires("libxosd/2.2.14")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _resolve_compiler(self, configured, names):
        # Same stale-toolchain guard as mtu/1.5.1 (traildb/0.6 origin):
        # the shared profile may point at a clang absolute path that no
        # longer exists on the device. Prefer the configured path only
        # when it exists, else resolve via PATH or ~/usr/local/bin.
        if configured and os.path.isabs(configured) and os.path.isfile(configured):
            return configured
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        home_bin = os.path.join(os.path.expanduser("~"), "usr", "local", "bin")
        for name in names:
            cand = os.path.join(home_bin, name)
            if os.path.isfile(cand):
                return cand
        return configured or names[0]

    def _compiler(self):
        comp = self.conf.get("tools.build:compiler_executables", check_type=dict) or {}
        configured = comp.get("c")
        candidates = [configured, os.environ.get("CC")]
        for cand in candidates:
            resolved = self._resolve_compiler(cand, ("clang", "cc"))
            if resolved and os.path.isfile(resolved):
                return resolved
        return self._resolve_compiler(configured or os.environ.get("CC"),
                                      ("clang", "cc"))

    def _xosd_flags(self):
        # R33: do not shell out to `xosd-config` (PATH-dependent); build
        # -I/-L/-l flags deterministically from the Conan dependency graph.
        includes = []
        libdirs = []
        for dep in self.dependencies.values():
            includes.extend(dep.cpp_info.includedirs)
            libdirs.extend(dep.cpp_info.libdirs)
        flags = (
            " ".join("-I%s" % p for p in includes)
            + " "
            + " ".join("-L%s" % p for p in libdirs)
            + " -lxosd -lX11 -lXext -lXinerama"
        )
        return flags

    def build(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "osdmixer/0.9 supports Linux and OHOS targets only, not %s" % self.settings.os
            )
        cc = self._compiler()
        self.output.info("HMBS diag compiler c=%s (configured=%s)" % (
            cc, (self.conf.get("tools.build:compiler_executables",
                               check_type=dict) or {}).get("c")))
        xosd = self._xosd_flags()
        # R33: CC/XOSD come from the Conan conf/graph, not bare shell vars.
        # Command-line assignments override the Makefile's `CC?=gcc` and its
        # backtick `XOSD=`xosd-config ...`` line. R9: -j1.
        # NOTE: the Makefile has no check/test target (audited no_tests),
        # so no upstream suite runs here; the marker below records that.
        self.run(
            'make -j1 CC="%s" XOSD="%s"' % (cc, xosd),
            cwd=self.source_folder,
            env="conanbuild",
        )
        self._emit_no_tests_marker()

    def _emit_no_tests_marker(self):
        upstream = {
            "status": "no_tests",
            "framework": "make",
            "command": "make check (upstream registers no tests)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "osdmixer-0.9 audited: the 2269-byte tarball holds only "
                      "Makefile + main.c; there is no tests/ or test/ "
                      "directory, the Makefile defines only all/clean/install "
                      "targets with no check/test target and no TESTS "
                      "registration; see test_package/MANIFEST.yml audit",
        }
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        print(msg, flush=True)
        self.output.info(msg)

    def package(self):
        # Do NOT run upstream `make install` (install -Dm 0755 to
        # $(DESTDIR)/usr/bin; OHOS lacks install(1) with -D — playumidi
        # precedent). Copy the built binary into the package bin/ instead.
        copy(self, "osdmixer", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
