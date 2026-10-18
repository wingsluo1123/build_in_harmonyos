#!/usr/bin/env python3
"""Consumer test for the tenyr toolchain (tas/tld/tsim)."""

import json
import os
import re
import time

from conan import ConanFile
from conan.tools.build import can_run

# Transient host fork/process-exhaustion signatures (same set as the main
# recipe).  On a resource-pressured HarmonyOS host the consumer shell can fail
# to fork the packaged binaries, producing no parseable result line; that is a
# transient host-resource failure, not a test failure, so the test command is
# retried a bounded number of times only when the captured output matches.
_TRANSIENT_FORK_SIGNATURES = (
    "Resource temporarily unavailable",
    "can't fork",
    "fork: retry",
    "fork failed: out of memory",
)


class TenyrTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def configure(self):
        # Same CI fork-pressure hardening as the main recipe: the default
        # Conan env-script body forks `printenv` per variable every time
        # `conanrun.sh`/`conanbuild.sh` is sourced.  Use the built-in
        # "function" deactivation mode so the sourced scripts only use shell
        # builtins (no `$(printenv ...)` fork) before running the consumer
        # test.  Environment semantics and test assertions are unchanged.
        self.conf.define("tools.env:deactivation_mode", "function")

    def test(self):
        if str(self.settings.os) == "OHOS" or can_run(self):
            # R34: pass the packaged binaries by absolute path so the test
            # genuinely depends on the package bin/.
            pkg = self.dependencies["tenyr"].package_folder
            bin_path = os.path.join(pkg, "bin")
            script = os.path.join(self.source_folder, "test_tenyr.sh")
            # The script uses bash constructs (set -o pipefail, heredocs), so
            # invoke bash explicitly (hmbs injects SHELL=/bin/sh which would
            # reject pipefail).  The OHOS profile's CONFIG_SHELL points at
            # /data/service/hnp/bin/bash.
            default_shell = (
                "/data/service/hnp/bin/bash"
                if str(self.settings.os) == "OHOS"
                else "bash"
            )
            shell = os.environ.get("CONFIG_SHELL", default_shell)
            logfile = os.path.join(self.build_folder, "test_package.log")
            cmd = '{shell} "{script}" "{bin}" > "{log}" 2>&1'.format(
                shell=shell, script=script, bin=bin_path, log=logfile
            )
            result_re = re.compile(
                r"tenyr test result:\s*(\d+)\s+passed,\s*(\d+)\s+failed"
            )
            # Bounded retry: only when no result line was produced AND the
            # captured output either carries a transient fork-exhaustion
            # signature or is empty (the consumer shell never forked the test
            # at all).  A real assertion failure always prints the result line,
            # so it is never retried and is surfaced unchanged.
            out = ""
            m = None
            for attempt in range(1, 4):
                self.run(cmd, env="conanrun", ignore_errors=True)
                out = ""
                if os.path.isfile(logfile):
                    with open(logfile, encoding="utf-8",
                              errors="replace") as f:
                        out = f.read()
                m = result_re.search(out or "")
                if m is not None:
                    break
                transient = any(
                    s in out for s in _TRANSIENT_FORK_SIGNATURES
                )
                if attempt < 3 and (transient or not out.strip()):
                    self.output.warn(
                        "tenyr test_package: transient host fork/process "
                        "exhaustion (attempt %d/3); retrying in 10s" % attempt
                    )
                    time.sleep(10)
                    continue
                break
            self.output.info("=== test_tenyr.sh log ===")
            for line in (out.splitlines() or [])[-10:]:
                self.output.info(line)
            # test_tenyr.sh prints one deterministic summary line:
            #   tenyr test result: 6 passed, 0 failed
            if m is None:
                raise RuntimeError(
                    "test_package: could not parse result line from test_tenyr.sh output:\n%s"
                    % (out or "")
                )
            passed = int(m.group(1))
            failed = int(m.group(2))
            discovered = passed + failed
            tp_result = {
                "executed": True,
                "passed": failed == 0 and discovered > 0,
                "command": cmd,
                "discovered": discovered,
                "passedCount": passed,
            }
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT="
                + json.dumps(tp_result, ensure_ascii=False)
            )
            if failed != 0 or discovered == 0:
                raise RuntimeError(
                    "test_package: tenyr consumer test failed: %d passed, %d failed"
                    % (passed, failed)
                )
