#!/usr/bin/env python3
"""Conan test_package — rtnppd 1.7b.

rtnppd is a privileged network daemon shipped as command-line binaries, so
the L1 test runs the real binaries (R34): test.sh exercises the getopt
startup paths of rtnppd/tnpppage/testq (usage banners, all exit(1) before
any daemonizing or network access) plus two OHOS-specific artifact checks
(OHOS/musl aarch64 ELF identity of all three binaries).
"""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException


class RtnppdTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot execute multi-line scripts
        # reliably; prefer bash. CI worker 提供 /data/service/hnp/bin/bash，
        # 但预检机该路径可能不存在（本轮 build 阶段同因失败），故按
        # CONFIG_SHELL -> SHELL (hmbs 注入 /bin/sh) -> PATH 顺序探测，
        # 仅当候选真实可执行时采用。
        bash = None
        for cand in (os.environ.get("CONFIG_SHELL"),
                     os.environ.get("SHELL"),
                     shutil.which("bash")):
            if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
                bash = cand
                break
        if bash is None:
            for cand in ("/bin/sh", shutil.which("sh")):
                if cand and os.path.isfile(cand):
                    bash = cand
                    break
        if bash is None:
            bash = "sh"
        self.output.info("using shell: %s" % bash)
        # test.sh runs 5 real assertions against the packaged binaries:
        #   1. `rtnppd -h` prints the usage banner and exits 1
        #   2. `tnpppage` (no args) prints the usage banner and exits 1
        #   3. `testq` (no args) prints the usage text and exits 1
        #   4. OHOS-specific: all three binaries are AArch64 ELF
        #   5. OHOS-specific: all three binaries use the OHOS/musl loader
        discovered = 5
        passed = 0
        try:
            self.run('"%s" test.sh' % bash, env="conanrun")
            passed = discovered
        except Exception as exc:
            self.output.error("test.sh failed: %s" % exc)

        # HMBS machine-evidence markers, printed on the Conan output stream.
        tp_result = {
            "executed": True,
            "passed": passed == discovered,
            "command": "%s test.sh" % bash,
            "discovered": discovered,
            "passedCount": passed,
        }
        print("HMBS_TEST_PACKAGE_RESULT=%s" % json.dumps(tp_result))

        # Upstream rtnppd 1.7b has no test suite (audited tarball, see
        # test_package/MANIFEST.yml upstream_tests_exist: false): the
        # Makefile defines only the default/rtnppd/testq/tnpppage/clean/
        # install/install.config/key targets, so `make check` has no rule
        # and the honest result is no_tests/0.
        ut_result = {
            "status": "no_tests",
            "framework": "make",
            "command": "make check",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "rtnppd-1.7b.tar.gz audited (sha256 "
                "06651a98c99048d9a211a92a68d8e5ed03ffdf2caf04904923a8ae7418a5eca4): "
                "no tests/ directory and no test source files anywhere in the "
                "tree; the Makefile defines only the default, rtnppd, testq, "
                "tnpppage, clean, install, install.config and key targets with "
                "no check/test/TESTS target, so `make check` has no rule to execute"
            ),
        }
        print("HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(ut_result))

        if passed != discovered:
            raise ConanException("test_package smoke tests failed")
