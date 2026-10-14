#!/usr/bin/env python3
"""Conan test_package for osdmixer 0.9 (L1 consumer test).

osdmixer is an application; the test validates that the packaged `osdmixer`
binary actually executes on the target through its help/usage path. With
fewer than 5 arguments main() prints the version/usage text and exits 0
*before* touching /dev/mixer or creating any xosd object, so the test needs
neither OSS audio nor an X server — it proves the binary runs and its
libxosd/X11 shared-library chain resolves.

Evidence markers:
- HMBS_TEST_PACKAGE_RESULT: discovered/passedCount parsed from the real
  "RESULT: P passed, F failed" trailer line of the script output.
- HMBS_UPSTREAM_TEST_RESULT: status=no_tests. Upstream ships no test suite
  (audited in MANIFEST.yml). Re-emitted here so evidence survives Conan
  cache hits (build() may be skipped on preflight).
"""

import json
import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanException


class OsdmixerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        bindir = dep.cpp_info.bindirs[0]
        binary = os.path.join(dep.package_folder, bindir, "osdmixer")
        if not os.path.isfile(binary):
            self.output.error("osdmixer binary not found at: %s" % binary)
            raise Exception("packaged binary missing: %s" % binary)

        test_script = os.path.join(self.recipe_folder, "test_osdmixer.sh")
        logfile = os.path.join(self.build_folder, "test_package.log")

        inner = "%s %s %s > %s 2>&1" % (
            shlex.quote("sh"),
            shlex.quote(test_script),
            shlex.quote(binary),
            shlex.quote(logfile),
        )
        self.run(inner, env="conanrun", ignore_errors=True)

        out = ""
        if os.path.isfile(logfile):
            with open(logfile, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        self.output.info(
            "test_osdmixer.sh log:\n" + "\n".join(out.splitlines()[-20:])
        )

        m = re.search(r"RESULT: (\d+) passed, (\d+) failed", out)
        if not m:
            raise ConanException(
                "test_osdmixer.sh produced no RESULT line - harness broken "
                "(log: %s)" % logfile
            )
        passed = int(m.group(1))
        failed = int(m.group(2))
        discovered = passed + failed
        ok = failed == 0 and discovered > 0

        marker = {
            "executed": True,
            "passed": ok,
            "command": "sh test_osdmixer.sh <pkg>/bin/osdmixer",
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
        if not ok:
            raise ConanException(
                "test_osdmixer.sh failed: %d/%d cases failed" % (failed, discovered)
            )

        upstream_marker = {
            "status": "no_tests",
            "framework": "make",
            "command": "make check (upstream registers no tests)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "osdmixer-0.9 上游无可接入的测试套件：2269 字节源码包内仅有 Makefile 与 main.c，Makefile 仅有 all/clean/install 目标而无 check/test 目标（详见 test_package/MANIFEST.yml 审计）；本 test_package 对打包二进制做 5 条消费端冒烟校验",
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            + json.dumps(upstream_marker, ensure_ascii=False)
        )
        self.output.info("osdmixer functional test_package passed")
