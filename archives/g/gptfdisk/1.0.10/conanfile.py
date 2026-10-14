#!/usr/bin/env python3
"""Conan recipe — gptfdisk 1.0.10 (GPT fdisk CLI suite: gdisk/cgdisk/sgdisk/fixparts).

Upstream: https://sourceforge.net/projects/gptfdisk/files/gptfdisk/1.0.10/
(gptfdisk-1.0.10.tar.gz, sha256 2abed61b...). Raw Makefile project (no
configure/CMake); builds four CLI tools:

  gdisk    - interactive GPT/MBR partition editor (links libuuid)
  sgdisk   - scriptable GPT editor (links libuuid + popt)
  cgdisk   - curses GPT editor (links libuuid + ncursesw)
  fixparts - MBR-to-GPT fixer (no external deps)

HarmonyOS PC (aarch64, os=OHOS) adaptation notes (see notes.md for detail):

  * The upstream Makefile picks its per-OS settings from `uname -s`
    (DETECTED_OS); on HarmonyOS `uname -s` is "HarmonyOS" so no branch
    matches and the Linux defaults (LDLIBS=-luuid, SGDISK_LDLIBS=-lpopt,
    CGDISK_LDLIBS=-lncursesw) are never applied. Upstream documents
    `TARGET=linux` as the supported knob for exactly this case ("pass
    TARGET={target_os} to cross-compile ... linux") - no source patch needed.
  * All external dependencies (libuuid/2.42.2, popt/1.16, ncurses/6.6) are
    published as STATIC binaries in the registry (shared=False), which is
    also what R26 requires for these system-name libraries.
  * gptcurses.cc hardcodes `#include <ncursesw/ncurses.h>`, while the conan
    ncurses package installs its headers flat in include/ (curses.h,
    ncurses.h). A one-line `ncursesw/ncurses.h` shim header pointing at
    <curses.h>, placed in the private build folder (R49, no shared-prefix
    injection), restores the systems-style layout without touching upstream
    sources (same technique as archives/a/audtty/0.1.12).
  * R33: CXX comes from tools.build:compiler_executables conf; CXXFLAGS are
    passed explicitly (upstream's Linux defaults restated because a
    command-line variable overrides the Makefile's `+=`).
  * Upstream test suite: the Makefile `test:` target runs ./gdisk_test.sh
    (only upstream test; 21 real checks over a 64 MiB scratch image, 10 per
    binary x 2 binaries + temp-disk setup). build() runs it via `sh` when
    can_run(self) and fails the recipe on any FAILED/rc!=0, emitting a
    machine-readable HMBS_UPSTREAM_TEST_RESULT marker.
"""

import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# gdisk_test.sh v1.0.10: per binary (gdisk, sgdisk) it prints 10 SUCCESS
# lines (create table / create partition / change name / change type /
# backup / delete / restore / change disk GUID / wipe / EOF) plus one
# "Temp disk sucessfully created" setup line => 21 checks total.
_UPSTREAM_EXPECTED_CHECKS = 21

# gdisk_test.sh pretty_print() wraps each marker in ANSI SGR codes
# (printf "\033[0;32m**SUCCESS**\033[m ..." / "\033[0;31m**FAILED**"),
# so strip CSI escape sequences before anchored marker matching.
_ANSI_CSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


class GptfdiskConan(ConanFile):
    name = "gptfdisk"
    version = "1.0.10"
    description = ("GPT fdisk - GPT/MBR disk partitioning CLI suite "
                   "(gdisk, cgdisk, sgdisk, fixparts)")
    license = "GPL-2.0-or-later"
    homepage = "https://www.rodsbooks.com/gdisk/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libuuid/2.42.2")
        self.requires("popt/1.16")
        self.requires("ncurses/6.6")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "gptfdisk requires a POSIX host (Linux/OHOS), got {}".format(
                    self.settings.os)
            )

    def layout(self):
        # The upstream Makefile is in-source only (no VPATH/out-of-tree
        # support), so the source folder doubles as the build folder.
        basic_layout(self)
        self.folders.build = "."
        self.folders.generators = "."

    def source(self):
        # Multi-mirror URL list + per-URL retry (clpbar/1.11.1 precedent):
        # SourceForge balancer truncates and its /download URL lacks a file
        # extension; conandata lists byte-identical *.dl.sourceforge.net
        # mirrors first (explicit filename required for query-string URLs).
        get(self, **self.conan_data["sources"], strip_root=True,
            retry=3, retry_wait=15)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _cxx(self):
        """CXX from Conan conf (R33), never from an unset shell var."""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = compilers.get("cpp") or compilers.get("c") or "clang++"
        return str(cxx)

    def _dep_dirs(self):
        """Include/lib dirs contributed by the (static) dependencies."""
        incs, libdirs = [], []
        for _ref, dep in self.dependencies.items():
            cppinfo = dep.cpp_info.aggregated_components()
            for d in cppinfo.includedirs:
                d = str(d)
                if d not in incs:
                    incs.append(d)
            for d in cppinfo.libdirs:
                d = str(d)
                if d not in libdirs:
                    libdirs.append(d)
        return incs, libdirs

    def _make_ncursesw_shim(self):
        """Provide <ncursesw/ncurses.h> for gptcurses.cc.

        The conan ncurses package installs headers flat (include/curses.h,
        include/ncurses.h); systems normally also ship an include/ncursesw/
        tree. Create a private shim header in the build folder (R49: no
        shared-prefix injection, no upstream source patch).
        """
        shim_root = os.path.join(self.build_folder, "ncursesw-compat")
        shim_dir = os.path.join(shim_root, "ncursesw")
        os.makedirs(shim_dir, exist_ok=True)
        shim = os.path.join(shim_dir, "ncurses.h")
        with open(shim, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("#pragma once\n#include <curses.h>\n")
        return shim_root

    def _pick_writable_tmpdir(self):
        """First writable scratch dir (gdisk_test.sh uses mktemp/dd).

        HMDFS ignores chmod/os.access, so probe with a real file write.
        Never hardcode /tmp (read-only on HarmonyOS, E002/R10).
        """
        candidates = []
        for key in ("TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(key, "").strip()
            if val and val not in candidates:
                candidates.append(val)
        candidates.append(os.path.join(self.build_folder, ".tmp"))
        home = os.environ.get("HOME", "")
        if home:
            candidates.append(os.path.join(home, "tmp"))
        for cand in candidates:
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".gptfdisk-write-probe")
                with open(probe, "w") as fh:
                    fh.write("ok")
                os.unlink(probe)
                return cand
            except OSError:
                continue
        return self.build_folder

    def _resolve_shell(self):
        """A shell that exists on the build machine (sh is enough for
        gdisk_test.sh; verified on device with /bin/sh)."""
        for name in ("sh", "bash"):
            found = shutil.which(name)
            if found:
                return found
        for cand in ("/bin/sh", "/usr/bin/bash"):
            if os.path.isfile(cand):
                return cand
        return "/bin/sh"

    # ------------------------------------------------------------------
    # build
    # ------------------------------------------------------------------
    def generate(self):
        vbe = VirtualBuildEnv(self)
        vbe.generate()

    def build(self):
        apply_conandata_patches(self)
        cxx = self._cxx()
        incs, libdirs = self._dep_dirs()
        shim = self._make_ncursesw_shim()
        include_flags = " ".join("-I" + p for p in [shim] + incs)
        lib_flags = " ".join("-L" + p for p in libdirs)
        # TARGET=linux: upstream-supported selector (uname -s == "HarmonyOS"
        # matches no branch, so the Linux defaults must be selected
        # explicitly). CXXFLAGS restates upstream's Linux defaults because a
        # command-line assignment overrides the Makefile's `CXXFLAGS+=`.
        cmd = (
            "make -j1 TARGET=linux"
            ' CXX="{cxx}"'
            ' CXXFLAGS="-O2 -Wall -D_FILE_OFFSET_BITS=64 {incs}"'
            ' LDFLAGS="{libs}"'
            ' LDLIBS="-luuid"'
            ' SGDISK_LDLIBS="-lpopt"'
            ' CGDISK_LDLIBS="-lncursesw"'
        ).format(cxx=cxx, incs=include_flags, libs=lib_flags)
        self.run(cmd, cwd=self.source_folder, env="conanbuild")

        for tool in ("gdisk", "cgdisk", "sgdisk", "fixparts"):
            path = os.path.join(self.source_folder, tool)
            if not os.path.isfile(path) or os.path.getsize(path) == 0:
                raise ConanInvalidConfiguration(
                    "gptfdisk build did not produce a usable '{}'".format(tool))
            self.output.info("built {}".format(path))

        if can_run(self):
            marker = self._run_upstream_tests()
            self._write_upstream_result(marker)
            if marker["failed"] != 0 or marker["passed"] != _UPSTREAM_EXPECTED_CHECKS:
                raise ConanInvalidConfiguration(
                    "gptfdisk upstream tests failed: {}/{} passed".format(
                        marker["passed"], _UPSTREAM_EXPECTED_CHECKS))
        else:
            self.output.warning(
                "cross-building: gdisk_test.sh runtime tests skipped")

    def _run_upstream_tests(self):
        """Run the upstream test suite (Makefile `test:` -> gdisk_test.sh).

        Real execution over a 64 MiB scratch file; the script drives both
        gdisk and sgdisk through create/name/type/backup/delete/restore/
        GUID/wipe/EOF scenarios and prints one SUCCESS|FAILED line per
        check. Numbers below come only from the process exit code and the
        counted SUCCESS/FAILED lines - no synthesis, fail closed.
        """
        tmpdir = self._pick_writable_tmpdir()
        env = os.environ.copy()
        env["TMPDIR"] = tmpdir
        env["TMP"] = tmpdir
        env["TEMP"] = tmpdir
        shell = self._resolve_shell()
        proc = subprocess.run(
            [shell, "./gdisk_test.sh"],
            cwd=self.source_folder,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            timeout=600,
        )
        out = proc.stdout or ""
        tail = "\n".join(out.strip().splitlines()[-25:])
        lines = [_ANSI_CSI_RE.sub("", line) for line in out.splitlines()]
        success = sum(1 for line in lines if line.startswith("**SUCCESS**"))
        failed = sum(1 for line in lines if line.startswith("**FAILED**"))
        self.output.info(
            "gdisk_test.sh rc={} SUCCESS={} FAILED={}".format(
                proc.returncode, success, failed))
        self.output.info("gdisk_test.sh tail:\n{}".format(tail))
        if proc.returncode != 0:
            raise ConanInvalidConfiguration(
                "gdisk_test.sh exited rc={} (see log tail above)".format(
                    proc.returncode))
        if failed != 0:
            raise ConanInvalidConfiguration(
                "gdisk_test.sh reported {} FAILED check(s)".format(failed))
        marker = {
            "status": "passed" if success == _UPSTREAM_EXPECTED_CHECKS else "failed",
            "framework": "gdisk_test.sh",
            "command": "sh ./gdisk_test.sh (Makefile test: target)",
            "checks_discovered": _UPSTREAM_EXPECTED_CHECKS,
            "checks_executed": success + failed,
            "passed": success,
            "failed": failed,
            "skipped": 0,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))
        return marker

    def _write_upstream_result(self, marker):
        try:
            path = os.path.join(self.build_folder, "upstream_test_result.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(marker, fh, indent=2)
        except OSError as exc:
            self.output.warning(
                "could not write upstream_test_result.json: {}".format(exc))

    # ------------------------------------------------------------------
    # package
    # ------------------------------------------------------------------
    def package(self):
        for tool in ("gdisk", "cgdisk", "sgdisk", "fixparts"):
            copy(self, tool, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        try:
            copy(self, "upstream_test_result.json", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "res"),
                 keep_path=False)
        except Exception as exc:  # noqa: BLE001 - evidence file is best effort
            self.output.warning(
                "copy upstream_test_result.json failed: {}".format(exc))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
