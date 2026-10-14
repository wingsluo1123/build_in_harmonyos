#!/usr/bin/env python3
"""Conan test_package — unscd 0.54.

unscd 0.54 is a single-file Name Service Cache Daemon (no library, no
upstream test suite). Consumer verification runs test.sh, which checks the
installed binary (`-V` version output, `--help` usage) and compiles+runs
test_nss.c — a real caller of the NSS APIs unscd caches
(getpwuid/getgrgid/gethostbyname).

test.sh itself prints both HMBS hard-gate markers with counts sourced from
its own check counters. This conanfile re-emits both markers in a finally
block (same numbers) so cache-hit rounds and early failures stay covered.
"""

import json
import os

from conan import ConanFile
from conan.errors import ConanException


class UnscdTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        unscd_bin = ""
        try:
            ref_name = self.tested_reference_str.split("/")[0]
            dep = self.dependencies[ref_name]
            for cand in (
                os.path.join(dep.package_folder, "bin", "unscd"),
                os.path.join(dep.package_folder, "bin", "nscd"),
            ):
                if os.path.isfile(cand):
                    unscd_bin = cand
                    self.output.info("unscd candidate: %s (%d bytes)" % (cand, os.path.getsize(cand)))
                    break
            if unscd_bin and os.path.exists(unscd_bin):
                try:
                    os.chmod(unscd_bin, 0o755)
                except Exception:
                    pass
            else:
                self.output.warning("unscd not found under package_folder %s" % dep.package_folder)
        except Exception as exc:
            self.output.warning("could not resolve unscd package_folder: %s" % exc)

        discovered = 4
        passed = 0
        if unscd_bin and os.path.isfile(unscd_bin):
            os.environ["CONAN_UNSCD_BIN"] = unscd_bin
            actual_cmd = "%s test.sh \"%s\"" % (bash, unscd_bin)
        else:
            actual_cmd = "%s test.sh" % bash
        try:
            self.run(actual_cmd, env="conanrun")
            passed = discovered
        except Exception as exc:
            self.output.error("test.sh failed: %s" % exc)
            raise
        finally:
            try:
                tp_marker = {
                    "executed": True,
                    "passed": passed == discovered,
                    "command": actual_cmd,
                    "discovered": discovered,
                    "passedCount": passed,
                }
                tp_msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_marker, ensure_ascii=False)
                print(tp_msg, flush=True)
                self.output.info(tp_msg)
            except Exception:
                pass
            try:
                upstream = {
                    "status": "no_tests",
                    "framework": "make",
                    "command": "make check",
                    "discovered": 0,
                    "executed": 0,
                    "passed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "reason": "unscd-0.54 audited: single nscd-0.54.c plus 223-byte Makefile with only all/clean targets; no tests dir, no test sources, no check target",
                }
                up_msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
                print(up_msg, flush=True)
                self.output.info(up_msg)
            except Exception:
                pass
        if passed != discovered:
            raise ConanException("test_package checks failed")
