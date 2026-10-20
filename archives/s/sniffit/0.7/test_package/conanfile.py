#!/usr/bin/env python3
"""Conan test_package for sniffit 0.7 (L1 consumer test).

sniffit is an application; the test validates that the packaged `sniffit`
binary actually runs on the target (linked libpcap/ncurses resolve, the
getopt/quit CLI paths work) through test_sniffit.sh: 5 real assertions
(binary inventory, `-v` exit code, exact "Sniffit Version 0.7" contract,
bare-invocation usage/privilege text in both root contexts, and an invalid
host negative control).

Evidence markers:
- HMBS_TEST_PACKAGE_RESULT: discovered/passedCount parsed from the real
  "RESULT: P passed, F failed" trailer line of the script output.
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


class SniffitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        binary = None
        for bindir in list(dep.cpp_info.bindirs) + ["bin", "sbin"]:
            candidate = os.path.join(dep.package_folder, bindir, "sniffit")
            if os.path.isfile(candidate):
                binary = candidate
                break
        if binary is None:
            raise ConanException(
                "packaged sniffit binary not found under %s" % dep.package_folder
            )

        workdir = os.path.join(self.build_folder, "sniffit-test")
        os.makedirs(workdir, exist_ok=True)
        tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or workdir
        )
        os.makedirs(tmpdir, exist_ok=True)

        test_script = os.path.join(self.recipe_folder, "test_sniffit.sh")
        logfile = os.path.join(self.build_folder, "test_package.log")

        # Custom vars ride inline so they survive regardless of env merge
        # semantics; env="conanrun" supplies the dependency run paths.
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
            with open(logfile, "r", encoding="utf-8", errors="replace") as handle:
                out = handle.read()
        self.output.info(
            "test_sniffit.sh log:\n" + "\n".join(out.splitlines()[-20:])
        )

        m = re.search(r"RESULT: (\d+) passed, (\d+) failed", out)
        if not m:
            raise ConanException(
                "test_sniffit.sh produced no RESULT line - harness broken "
                "(log: %s)" % logfile
            )
        passed = int(m.group(1))
        failed = int(m.group(2))
        discovered = passed + failed
        ok = failed == 0 and discovered > 0

        marker = {
            "executed": True,
            "passed": ok,
            "command": "sh test_sniffit.sh <pkg>/bin/sniffit <workdir>",
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
        if not ok:
            raise ConanException(
                "test_sniffit.sh failed: %d/%d cases failed" % (failed, discovered)
            )

        # Upstream has no test suite (audited in test_package/MANIFEST.yml):
        # status=no_tests with zero counts. Re-emitted here so the evidence
        # the gate requires is present even on cache-hit preflight rounds.
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
                "sniffit 0.7 上游无可接入的测试套件：源码树无 tests/test 目录，"
                "顶层与 src/Makefile.am 均无 TESTS/check_PROGRAMS 注册，"
                "configure.ac 仅做特性探测（详见 test_package/MANIFEST.yml 审计）；"
                "本 test_package 对打包二进制做 5 条消费端校验"
            ),
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            + json.dumps(upstream_marker, ensure_ascii=False)
        )
        self.output.info("sniffit functional test_package passed")
