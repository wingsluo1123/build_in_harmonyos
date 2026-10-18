#!/usr/bin/env python3
"""Conan test_package for msktutil 1.2.2 (L1 consumer test).

msktutil is an application; the test validates that the packaged
`msktutil` binary actually runs on the target through a self-contained
smoke script with 6 real offline assertions (no Active Directory needed):
  1. `msktutil --version` exits 0
  2. `--version` output is exactly "msktutil version 1.2.2"
  3. `msktutil --help` exits 0
  4. `--help` output contains the "--help" usage text
  5. negative control: `msktutil --service` (missing argument) exits 1
     with an "Error:" message (proves the harness observes real failures)

Evidence markers:
- HMBS_TEST_PACKAGE_RESULT: discovered/passedCount parsed from the real
  "RESULT: P passed, F failed" trailer line of the script output (real counts,
  not an estimate).
- HMBS_UPSTREAM_TEST_RESULT: status=no_tests. Upstream ships no test suite
  (audited in MANIFEST.yml). The marker is emitted here so evidence is
  present even though the recipe build() itself runs no upstream tests.
"""

import json
import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanException


class MsktutilTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Locate the packaged msktutil binary in the tested package's bin dir
        # (Conan 2 AutotoolsToolchain forces --sbindir=${prefix}/bin, so the
        # upstream sbin install lands in <pkg>/bin/, matching
        # package_info.bindirs — same verified layout as the adcli recipe).
        dep = self.dependencies[self.tested_reference_str]
        bindir = dep.cpp_info.bindirs[0]
        binary = os.path.join(dep.package_folder, bindir, "msktutil")
        if not os.path.isfile(binary):
            self.output.error("msktutil binary not found at: %s" % binary)
            raise Exception("packaged binary missing: %s" % binary)

        # A writable working dir (kept inside the per-task TMPDIR/TEMP that
        # HMBS injects; HMFS /tmp is read-only).
        workdir = os.path.join(self.build_folder, "msktutil-test")
        os.makedirs(workdir, exist_ok=True)
        tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or workdir
        )
        os.makedirs(tmpdir, exist_ok=True)

        test_script = os.path.join(self.recipe_folder, "test.sh")
        logfile = os.path.join(self.build_folder, "test_package.log")

        # Run the smoke script (STDOUT of the script itself is redirected to
        # logfile; never to the workdir directory). Custom TMP vars ride
        # inline so they survive regardless of env merge semantics;
        # env="conanrun" supplies the dependency run paths.
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
            "test.sh log:\n" + "\n".join(out.splitlines()[-20:])
        )

        # Machine-evidence count comes from the script's deterministic
        # "RESULT: P passed, F failed" trailer line (real assertion results).
        m = re.search(r"RESULT: (\d+) passed, (\d+) failed", out)
        if not m:
            raise ConanException(
                "test.sh produced no RESULT line - harness broken "
                "(log: %s)" % logfile
            )
        passed = int(m.group(1))
        failed = int(m.group(2))
        discovered = passed + failed
        ok = failed == 0 and discovered > 0

        marker = {
            "executed": True,
            "passed": ok,
            "command": "sh test.sh <pkg>/bin/msktutil <workdir>",
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
        if not ok:
            raise ConanException(
                "test.sh failed: %d/%d cases failed"
                % (failed, discovered)
            )

        # Upstream has no test suite (audited in test_package/MANIFEST.yml):
        # status=no_tests with zero counts.
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
                "msktutil 1.2.2 上游无可接入的测试套件：release 源码树无 tests/ "
                "目录或任何测试文件，Makefile.in 无 check/TESTS 目标（仅 "
                "all/clean/distclean/install/dist/distcheck，distcheck 仅回显"
                "版本号），configure.ac 未注册任何测试（详见 "
                "test_package/MANIFEST.yml 审计）；本 test_package 对打包二进制"
                "做 5 条离线消费端冒烟校验"
            ),
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            + json.dumps(upstream_marker, ensure_ascii=False)
        )
        self.output.info("msktutil functional test_package passed")
