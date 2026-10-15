#!/usr/bin/env python3
"""Conan test_package for vish 0.0.20130812.

Runs two OHOS-specific checks against the installed `vish` binary:

  1. `vish --version` — exit code 0 and output contains "0.0.20130812"
     (exercises the real linked executable and the PACKAGE/VERSION macros;
     a broken/empty binary would fail the non-empty-output assertion).
  2. `vish --scan` — exit code 0. This is the real VISA path:
     viOpenDefaultRM -> viFindRsrc -> viClose. With the librevisa portable
     core (no hardware) viFindRsrc returns SUCCESS with 0 devices, so the
     command exits 0. It proves the executable links libvisa.a correctly
     and the VISA resource-manager symbols resolve at runtime.

No upstream test suite exists (vish 0.0.20130812 has no tests/ directory
and Makefile.am declares no check target) — upstream_test_total=0, audited
in MANIFEST.yml. Emits HMBS_TEST_PACKAGE_RESULT with real counts.

NOTE: OHOS /system/bin/sh (mksh) cannot execute ELF binaries directly, so
the checks are wrapped with a probed POSIX shell (zlib/libuio precedent).
"""
import json
import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment


def _resolve_shell():
    """First existing shell for running the test binary."""
    for cand in (
        os.environ.get("CONFIG_SHELL"),
        os.environ.get("SHELL"),
        "/bin/sh",
        "/system/bin/sh",
        "/data/service/hnp/bin/bash",
    ):
        if cand and os.path.isfile(cand):
            return cand
    for name in ("bash", "sh"):
        found = shutil.which(name)
        if found:
            return found
    return "/bin/sh"


class VishTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        result = {
            "executed": True,
            "passed": False,
            "command": "sh test.sh (vish --version && vish --scan)",
            "discovered": 2,
            "passedCount": 0,
        }
        bash = _resolve_shell()
        # test.sh is the authoritative runner (declared in MANIFEST.yml):
        #   check 1: vish --version exits 0 with the version string;
        #   check 2: vish --scan exits 0 (real VISA resource-manager path).
        # A failing assertion makes test.sh exit non-zero, which self.run
        # propagates as an exception.
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test.sh")
        try:
            self.run(f'"{bash}" "{script}"', env="conanrun")
            result["passedCount"] = 2
        except Exception:
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False)
            )
            raise
        result["passed"] = True
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False)
        )

        # Upstream has no test suite (audited in MANIFEST.yml).
        upstream = {
            "status": "no_tests",
            "framework": "none",
            "command": "none (upstream vish 0.0.20130812 has no test suite)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "upstream_tests_exist=false per test_package/MANIFEST.yml "
                "upstream_test_audit: no tests/ directory, no check_PROGRAMS/"
                "TESTS target (Makefile.am only declares bin_PROGRAMS=vish + "
                "dist_man_MANS=vish.1), no *_test files, no CI test config."
            ),
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        )
