#!/usr/bin/env python3
"""Conan test_package for rarcrack 0.2-20240214-413ea3a (L1 consumer test).

rarcrack is an application; the test validates that the packaged `rarcrack`
binary actually runs on the target through a self-contained shell script
with 6 real assertions: bare-invocation USAGE text, --help text, missing
archive error path, invalid --type warning path, thread-count clamp path
(HMFS-redirected output), and a negative side-effect control (no status
*.xml may be created when cracking never starts, proving the harness
observes real behavior instead of faking success).

Deliberately no real cracking is started: starting crack_start() without
the external unrar/7z/unzip helpers on the target would spin forever.
All 6 cases return before crack_start() and complete in under a second.

Evidence markers:
- HMBS_TEST_PACKAGE_RESULT: discovered/passedCount parsed from the real
  "RESULT: P passed, F failed" trailer line of the script output (real counts,
  not an estimate).
- HMBS_UPSTREAM_TEST_RESULT: status=no_tests. Upstream ships no test suite
  (audited in MANIFEST.yml). The marker is re-emitted here so evidence
  survives Conan cache hits (build() may be skipped on preflight).
"""

import json
import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanException


class RarcrackTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        bindir = dep.cpp_info.bindirs[0]
        binary = os.path.join(dep.package_folder, bindir, "rarcrack")
        if not os.path.isfile(binary):
            self.output.error("rarcrack binary not found at: %s" % binary)
            raise Exception("packaged binary missing: %s" % binary)

        # A writable working dir (kept inside the per-task TMPDIR/TEMP that
        # HMBS injects; HMFS /tmp is read-only).
        workdir = os.path.join(self.build_folder, "rarcrack-test")
        os.makedirs(workdir, exist_ok=True)
        tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or workdir
        )
        os.makedirs(tmpdir, exist_ok=True)

        test_script = os.path.join(self.recipe_folder, "test_rarcrack.sh")
        logfile = os.path.join(self.build_folder, "test_package.log")

        # Custom vars ride inline so they survive regardless of env merge
        # semantics; env="conanrun" supplies the dependency run paths.
        # The script contract is: sh test_rarcrack.sh <binary> <workdir>
        inner = "%s %s %s %s %s %s %s > %s 2>&1" % (
            "TMPDIR=%s" % shlex.quote(tmpdir),
            "TMP=%s" % shlex.quote(tmpdir),
            "TEMP=%s" % shlex.quote(tmpdir),
            shlex.quote("sh"),
            shlex.quote(test_script),
            shlex.quote(binary),
            shlex.quote(workdir),
            shlex.quote(logfile),
        )
        self.run(inner, env="conanrun", ignore_errors=True)

        out = ""
        if os.path.isfile(logfile):
            with open(logfile, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        self.output.info(
            "test_rarcrack.sh log:\n" + "\n".join(out.splitlines()[-20:])
        )

        # Machine-evidence count comes from the script's deterministic
        # "RESULT: P passed, F failed" trailer line (real assertion results).
        m = re.search(r"RESULT: (\d+) passed, (\d+) failed", out)
        if not m:
            raise ConanException(
                "test_rarcrack.sh produced no RESULT line - harness broken "
                "(log: %s)" % logfile
            )
        passed = int(m.group(1))
        failed = int(m.group(2))
        discovered = passed + failed
        ok = failed == 0 and discovered > 0

        marker = {
            "executed": True,
            "passed": ok,
            "command": "sh test_rarcrack.sh <pkg>/bin/rarcrack <workdir>",
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
        if not ok:
            raise ConanException(
                "test_rarcrack.sh failed: %d/%d cases failed"
                % (failed, discovered)
            )

        # Upstream has no test suite (audited in test_package/MANIFEST.yml):
        # status=no_tests with zero counts. Re-emitted here so the evidence
        # the gate requires is present even when the recipe build() itself
        # runs no upstream tests (build()/package() may be cache-hit).
        upstream_marker = {
            "status": "no_tests",
            "framework": "make",
            "command": "make check (upstream registers no tests)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "rarcrack 0.2-20240214-413ea3a ships no automated tests: "
                "the source tree has no tests/ directory or test harness, "
                "and the Makefile defines only all/debug/clean/install/"
                "uninstall targets (see test_package/MANIFEST.yml audit)."
            ),
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            + json.dumps(upstream_marker, ensure_ascii=False)
        )
        self.output.info("rarcrack functional test_package passed")
