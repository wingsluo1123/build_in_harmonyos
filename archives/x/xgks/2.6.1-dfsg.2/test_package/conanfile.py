#!/usr/bin/env python3
"""Conan test_package — xgks 2.6.1-dfsg.2 (Conan L1 official test).

Builds test.c against the packaged static libraries (R34: real GKS API
usage — gopengks/gopenws(MO)/gpolyline/gpolymarker/gfillarea plus a
non-empty-metafile assertion, 6 checks) and emits HMBS machine-evidence
markers. Upstream ships no automated test suite (audited, see
test_package/MANIFEST.yml), so the upstream marker is the honest
no_tests/0 result.
"""

import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import replace_in_file

CONSUMER_ASSERTS = 6


class XgksTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # xmhtml/1.1.10 test_package precedent: the OHOS profile pins
        # tools.build:compiler_executables to /data/service/hnp/bin/clang,
        # which does not exist on every worker (this round: CMake Error
        # CMAKE_C_COMPILER .../hnp/bin/clang broken). Rewrite the
        # toolchain to compilers that exist; VirtualRunEnv is explicit
        # because test() runs with env="conanrun".
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["CMAKE_C_COMPILER"] = self._compiler_executable(
                "c", "clang")
            tc.cache_variables["CMAKE_CXX_COMPILER"] = self._compiler_executable(
                "cpp", "clang++")
        tc.generate()
        if str(self.settings.os) == "OHOS":
            self._patch_cmake_toolchain_compilers()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanException("xgks target consumers are not runnable here")
        discovered = CONSUMER_ASSERTS
        passed = 0
        exe = os.path.join(self.cpp.build.bindirs[0], "test_xgks")
        self.run('"{}"'.format(exe), env="conanrun")
        # Exit 0 above means all 6 printed checks passed (test.c returns
        # non-zero on the first failing check, so success is all-or-nothing).
        passed = discovered

        tp_result = {
            "executed": True,
            "passed": passed == discovered,
            "command": "./test_xgks (GKS open + MO workstation + 3 primitives + close + metafile size)",
            "discovered": discovered,
            "passedCount": passed,
        }
        print("HMBS_TEST_PACKAGE_RESULT={}".format(json.dumps(tp_result, separators=(",", ":"))))

        ut_result = {
            "status": "no_tests",
            "framework": "custom Makefile",
            "command": "make test (interactive X11 demos, disabled by Debian)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "xgks 2.6.1+dfsg.2 orig.tar.gz audited (1688680 bytes, sha256 "
                "451dd35080fd3e2fc1f5ed83b8b86e29c5ad0af2adf4c4d08ff13643ece641ab): "
                "698 archive entries, no tests/ or test/ directory and no test "
                "runner; the only test entry point is src/progs 'test: all' which "
                "runs interactive X11 demos (pmark/pline need a display, gksdemo "
                "is interactive) and Debian's debian/rules overrides "
                "dh_auto_test with 'Testing disabled as tests are interactive'; "
                "configure.in probes only compilers/X11/troff, no test framework. "
                "Functional verification is the test_package consumer driving "
                "the real C API against a display-independent MO workstation."
            ),
        }
        print("HMBS_UPSTREAM_TEST_RESULT={}".format(json.dumps(ut_result, separators=(",", ":"))))

        if passed != discovered:
            raise ConanException("test_package checks failed")

    def _compiler_executable(self, key, fallback_name):
        import shutil
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        configured = executables.get(key)
        if configured and os.path.isfile(configured):
            return configured
        found = shutil.which(fallback_name)
        return found or configured or fallback_name

    def _patch_cmake_toolchain_compilers(self):
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        replacements = {
            "/data/service/hnp/bin/clang++": self._compiler_executable(
                "cpp", "clang++"
            ),
            "/data/service/hnp/bin/clang": self._compiler_executable("c", "clang"),
        }
        for old, new in replacements.items():
            replace_in_file(self, toolchain, old, new, strict=False)
