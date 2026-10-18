#!/usr/bin/env python3
"""Conan test_package --- scrot 2.0.0.

R34: test_package must substantially exercise the tested package.
scrot is an X11 CLI binary (not a library), so tests execute the
binary directly. All three probes are headless-safe: they do not
need an X display (no screenshot is taken).

Tests (driven by test_scrot.py, L0c source file):
  1. scrot --version       - binary runs and reports version 2.0.0
  2. scrot --help           - help text is produced (non-empty gate)
  3. scrot --list-options   - machine-readable option list is produced (non-empty gate)

HMBS machine evidence: test() emits HMBS_TEST_PACKAGE_RESULT with real
case counters (3 CLI probes; self.run raises on failure so reaching the
marker means 3/3 passed) and re-emits HMBS_UPSTREAM_TEST_RESULT
status=no_tests every run (upstream ships no test suite; audited in
MANIFEST.yml) so the evidence gate passes even on cache hits.
"""

import json
import os

from conan import ConanFile
from conan.tools.build import can_run


class ScrotTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    # L0c: test_package/ must contain a test source file besides
    # conanfile.py (.py/.c/.sh); test_scrot.py is the real driver
    # (sl/5.02-r1 + toybox/0.8.9 precedent), executed below.
    exports_sources = "test_scrot.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _hmbs_emit(self, line):
        self.output.info(line)
        try:
            print(line, flush=True)
        except Exception:
            pass

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: build verified, runtime tests skipped")
            return
        scrot_bin = os.path.join(
            self.dependencies["scrot"].package_folder, "bin", "scrot"
        )
        # Real driver: test_scrot.py runs the 3 headless-safe CLI probes
        # (--version/--help/--list-options) with per-case assertions and
        # non-empty-output gates; self.run raises on script failure.
        script = os.path.join(self.source_folder, "test_scrot.py")
        self.run(f'python3 "{script}" "{scrot_bin}"', env="conanrun")
        # All three probes exited 0 (self.run raises otherwise): 3 real cases.
        test_pkg = {
            "executed": True,
            "passed": True,
            "command": "python3 test_scrot.py (scrot --version && scrot --help && scrot --list-options)",
            "discovered": 3,
            "passedCount": 3,
        }
        self._hmbs_emit("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, separators=(",", ":")))
        # Upstream ships no test suite (no tests/ dir, no TESTS in
        # Makefile.am, no `make check` target); re-emit every run.
        upstream_marker = {
            "status": "no_tests",
            "framework": "none",
            "command": "make check",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "scrot 2.0.0 upstream ships no test suite: no tests/ dir, top-level Makefile.am SUBDIRS=src with no TESTS, src/Makefile.am only bin_PROGRAMS=scrot; make check has no target",
        }
        self._hmbs_emit("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker, separators=(",", ":")))
