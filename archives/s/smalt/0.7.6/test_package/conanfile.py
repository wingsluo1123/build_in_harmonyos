#!/usr/bin/env python3
"""Conan test_package for smalt 0.7.6 - HarmonyOS consumer validation.

Two layers, both driven from test():

Layer 1 (always runs, host independent) - ohos_abi_check.py inspects the
    *packaged* executables instead of running them:
      A1 ELF64 + e_machine == EM_AARCH64 + e_type == ET_DYN (PIE)
      A2 .interp == /lib/ld-musl-aarch64.so.1  (the OHOS musl loader)
      A3 DT_NEEDED is exactly [libc.so] - zlib is linked statically and musl's
         libm/libpthread are empty compatibility archives (R26)
      A4 no DT_RPATH/DT_RUNPATH
    It is pure Python ELF parsing with no external tool, so it also runs on the
    macOS dev box that cross-compiles with the OHOS SDK but cannot execute an
    aarch64-linux-ohos ELF - that host must still validate the artifact rather
    than pass silently.  It is also what keeps the CI L1e destructive reverse
    check meaningful when cross building: move bin/ away and this layer fails.

Layer 2 (can_run only) - ohos_e2e_test.py drives 13 checks against the packaged
    binaries on a real HarmonyOS host: F1-F8 cover the documented CLI surface
    (help/usage/error paths, `smalt check`, a full index+map run whose five SAM
    records must match the values measured on unmodified upstream sources, an
    unmappable read, and the companion readstats/fetchseq tools) and H1-H5 are
    HarmonyOS specific (executing the signed installed product in place, the
    statically linked zlib decompressing a gzipped reference on musl,
    multi-threaded mapping staying deterministic, index files living on
    HMDFS-backed storage and being reusable by a second process, and musl's
    rand()/srand48() reproducing identical alignments).

Upstream's own suite (six make check drivers plus the two C test programs) runs
in the recipe's build(), not here; see test_package/MANIFEST.yml for the audit
and the single counting method used across every artifact of this adaptation.

Nothing is ever copied, renamed or hard-linked before execution: HarmonyOS
refuses to run an ELF that crossed the .codesign signing boundary, so every
check invokes the installed product at its real path.  Scratch files go to the
conan build folder, never /tmp (read-only erofs on OHOS, E002).
"""
import os
import re
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run

# A1-A4 artifact/ABI checks.
EXPECTED_ABI_CHECKS = 4
# F1-F8 functional + H1-H5 HarmonyOS specific on-device checks.
EXPECTED_E2E_CHECKS = 13


class SmaltTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        # run=True: VirtualRunEnv only injects bin/ of run dependencies into
        # PATH, and smalt is an application package.
        self.requires(self.tested_reference_str, run=True)

    def _bindir(self):
        """Absolute bin/ of the tested package (do not rely on PATH alone)."""
        dep = self.dependencies.get("smalt")
        if dep is None:
            raise ConanException("smalt dependency missing from the graph")
        rel = "bin"
        try:
            if dep.cpp_info.bindirs:
                rel = dep.cpp_info.bindirs[0]
        except Exception:
            rel = "bin"
        cand = rel if os.path.isabs(rel) else os.path.join(dep.package_folder, rel)
        self.output.info("smalt package_folder=%s bindir=%s"
                         % (dep.package_folder, cand))
        return cand

    def _run_suite(self, script, extra_args, expected, label):
        """Run one suite, echo its log and enforce its RESULT line."""
        python = sys.executable or "python3"
        path = os.path.join(self.recipe_folder, script)
        if not os.path.isfile(path):
            raise ConanException("smalt: %s is missing from test_package" % script)
        log = os.path.join(self.build_folder, "%s.log" % label)
        # Conan 2's self.run() does not return the output, so capture it to a
        # file and read it back.  Without a layout() the test package runs in
        # its own source folder, so the capture file is removed again once its
        # text has been echoed into the conan output: the build log keeps the
        # full text for CI triage and no stray file is left inside archives/.
        rc = self.run('"%s" "%s" %s > "%s" 2>&1'
                      % (python, path, extra_args, log), ignore_errors=True)
        try:
            with open(log, encoding="utf-8", errors="replace") as fh:
                out = fh.read()
        except OSError:
            out = ""
        try:
            os.remove(log)
        except OSError:
            pass
        self.output.info(out.strip()[-6000:])
        m = re.search(r"RESULT: passed=(\d+) failed=(\d+)", out)
        if not m:
            raise ConanException(
                "smalt: %s produced no RESULT summary line (rc=%s)" % (label, rc))
        passed, failed = int(m.group(1)), int(m.group(2))
        self.output.info("smalt %s: passed=%d failed=%d (rc=%s)"
                         % (label, passed, failed, rc))
        if failed or rc != 0:
            raise ConanException(
                "smalt: %s reported %d failing check(s) - see the log above"
                % (label, failed))
        if passed != expected:
            raise ConanException(
                "smalt: %s ran %d checks, expected %d" % (label, passed, expected))

    def test(self):
        bin_dir = self._bindir()

        # -- Layer 1: HarmonyOS artifact/ABI checks (host independent) --
        self._run_suite("ohos_abi_check.py", '--bindir "%s"' % bin_dir,
                        EXPECTED_ABI_CHECKS, "abi")

        # -- Layer 2: on-device consumer suite --
        if not can_run(self) or self._local_ohos_simulation():
            self.output.info(
                "cross building: an aarch64-linux-ohos ELF cannot execute on "
                "this host, so the %d on-device checks (F1-F8, H1-H5) run on "
                "the HarmonyOS CI worker; the artifact/ABI layer above did "
                "execute against the packaged binaries" % EXPECTED_E2E_CHECKS)
            return

        workdir = os.path.join(self.build_folder, "e2e-workdir")
        self._run_suite("ohos_e2e_test.py",
                        '--bindir "%s" --workdir "%s"' % (bin_dir, workdir),
                        EXPECTED_E2E_CHECKS, "e2e")

    def _local_ohos_simulation(self):
        """True when the host only *simulates* OHOS settings (macOS dev box).

        `conan-verify --profile ohos-local` passes the same OHOS profile as both
        -pr:h and -pr:b, so can_run() can report True even though the host
        cannot execute an aarch64-linux-ohos ELF.  The local profile marks
        itself with user.build:flex_bison_native (precedent: libidl2 0.8.14,
        secpwgen 1.3, ylva 1.7); ci/conan/profiles/ohos-aarch64 does not set it,
        so the real HarmonyOS worker still runs the full on-device suite.
        """
        try:
            return bool(self.conf.get("user.build:flex_bison_native",
                                      default=False))
        except Exception:
            return False
