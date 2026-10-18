#!/usr/bin/env python3
"""Conan test_package — libmems 1.6.0-4725 (installed-package consumer test).

The consumer builds and runs test_mems.c against the installed libMems.
The test exercises the real libMems C API (twister.h MT19937 generator:
SetTwisterSeed / RandTwisterUnsigned / RandTwisterDouble /
CreateTwisterSeed) with four deterministic assertions, including the
public MT19937 reference vector (seed 5489 -> 3499211612). The alignment
core headers all require libGenome/libMUSCLE/Boost headers, so the
dependency-free twister API is the honest consumer surface until the
dependency chain (libgenome/libmuscle) is published.

Evidence markers (rule4 hard gates):
- HMBS_TEST_PACKAGE_RESULT: discovered/passedCount parsed from the test
  binary's own "RESULT: N passed, M failed" line (single deterministic
  source, fail-closed when the line is absent).
- HMBS_UPSTREAM_TEST_RESULT: status=no_tests. Upstream ships no test
  suite (audit in MANIFEST.yml). Emitted here every round so evidence
  also exists on cache-hit rounds where the main build() output is
  skipped ("Already installed!").
"""

import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class LibmemsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("NOT_RUN LIBMEMS_TARGET_CONSUMER=0/1 reason=cross_building")
            self._emit_upstream_marker()
            return

        shell = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or "/bin/sh"
        tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or os.path.join(self.build_folder, ".tmp")
        )
        os.makedirs(tmpdir, exist_ok=True)

        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        executable = os.path.join(self.cpp.build.bindirs[0], "test_mems" + suffix)
        if not os.path.isfile(executable):
            raise ConanException("test_mems binary not found: %s" % executable)
        logfile = os.path.join(self.build_folder, "test_package.log")
        inner = '"%s" > "%s" 2>&1' % (executable, logfile)
        if shutil.which("timeout"):
            cmd = "timeout 90 %s" % inner
        elif os.path.isfile("/data/service/hnp/bin/timeout"):
            cmd = "/data/service/hnp/bin/timeout 90 %s" % inner
        else:
            cmd = inner

        env_vars = Environment()
        env_vars.define("TMPDIR", tmpdir)
        env_vars.define("TMP", tmpdir)
        env_vars.define("TEMP", tmpdir)
        with env_vars.vars(self).apply():
            self.run(cmd, env=None, ignore_errors=True)

        out = ""
        if os.path.isfile(logfile):
            with open(logfile, "r", encoding="utf-8", errors="replace") as handle:
                out = handle.read()
        self.output.info("test_mems log:\n" + "\n".join(out.splitlines()[-12:]))

        match = re.search(r"RESULT: (\d+) passed, (\d+) failed", out)
        if not match:
            raise ConanException("test_mems produced no RESULT line - harness broken")
        passed = int(match.group(1))
        failed = int(match.group(2))
        discovered = passed + failed
        ok = failed == 0 and discovered > 0

        marker = {
            "executed": True,
            "passed": ok,
            "command": executable,
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
        if not ok:
            raise ConanException("test_mems failed: %d/%d cases failed" % (failed, discovered))
        self._emit_upstream_marker()
        self.output.info("libmems consumer test_package passed")

    def _emit_upstream_marker(self):
        # Upstream test marker: libmems 1.6.0+4725 ships no test suite.
        # Audit basis (see test_package/MANIFEST.yml upstream_test_audit):
        # no testsuite/ directory, no TESTS/check_PROGRAMS in either
        # Makefile.am, only a commented-out wx-dependent TestSML sketch.
        upstream_marker = {
            "status": "no_tests",
            "framework": "autotools",
            "command": "make check (upstream provides no check target)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "libmems 1.6.0+4725 上游发布包无任何测试套件：tarball 无 testsuite/ 目录；"
                "顶层与 libMems/Makefile.am 均无 TESTS/check_PROGRAMS 接线；"
                "唯一的 TestSML 痕迹是注释掉的草稿且依赖 wxWidgets，从未接入任何测试目标；"
                "configure.ac 无测试接线"
            ),
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker, ensure_ascii=False))
