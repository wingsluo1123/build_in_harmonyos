#!/usr/bin/env python3
"""Conan test_package — lcm 1.3.11 consumer test.

Builds a C consumer (test_lcm.c) against the INSTALLED liblcm via CMakeDeps
(lcm::lcm + its glib closure) and runs it on the native OHOS target.  The
consumer performs exactly 6 real LCM memq lifecycle checks, each printing one
"CHECK-OK: <name>" line; those deterministic lines are counted for the
HMBS_TEST_PACKAGE_RESULT machine-evidence marker (exit-code-0 alone is not
proof).

Upstream evidence: the 12-case upstream gtest suite runs in the main recipe
build() and persists res/upstream_test_result.json in the package, so this
re-emits HMBS_UPSTREAM_TEST_RESULT from that file on every preflight round
(cache-hit rounds skip the main build, the gate still needs the marker).
"""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import replace_in_file


# test_lcm.c performs exactly 6 checks, each printing one "CHECK-OK: <name>".
CONSUMER_CHECK_COUNT = 6


class LcmTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _compiler_executable(self, key, fallback_name):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        configured = executables.get(key)
        if configured and os.path.isfile(configured):
            return configured
        found = shutil.which(fallback_name)
        return found or configured or fallback_name

    def _patch_cmake_toolchain_compilers(self):
        # Stale-toolchain guard (repo convention): the OHOS profile pins
        # /data/service/hnp/bin/clang(++), which may not exist on the current
        # worker. Resolve to an existing binary and rewrite the generated
        # conan_toolchain.cmake.
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        replacements = {
            "/data/service/hnp/bin/clang++": self._compiler_executable("cpp", "clang++"),
            "/data/service/hnp/bin/clang": self._compiler_executable("c", "clang"),
        }
        for old, new in replacements.items():
            replace_in_file(self, toolchain, old, new, strict=False)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        if str(self.settings.get_safe("os")) == "OHOS":
            tc.cache_variables["CMAKE_C_COMPILER"] = self._compiler_executable("c", "clang")
            tc.cache_variables["CMAKE_CXX_COMPILER"] = self._compiler_executable(
                "cpp", "clang++"
            )
        tc.generate()
        if str(self.settings.get_safe("os")) == "OHOS":
            self._patch_cmake_toolchain_compilers()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _find_bin(self):
        for b in self.cpp.build.bindirs:
            cand = os.path.join(b, "test_lcm")
            if os.path.isfile(cand):
                return cand
        return os.path.join(self.cpp.build.bindirs[0], "test_lcm")

    def test(self):
        if not can_run(self):
            self.output.info("cannot run test_package on this host; skipping run")
            return
        executable = self._find_bin()
        if not os.path.isfile(executable):
            raise ConanException("test binary missing: %s" % executable)
        # Run the consumer, capturing its stdout to a log so the passed-count
        # comes from the deterministic "CHECK-OK:" lines the program actually
        # emitted (never inferred from the exit code alone).
        log = os.path.join(self.build_folder, "test_package.log")
        discovered = CONSUMER_CHECK_COUNT
        passed = 0
        try:
            self.run(
                '"%s" > "%s" 2>&1' % (executable, log),
                env="conanrun",
                ignore_errors=True,
            )
        except Exception as exc:  # noqa: BLE001
            self.output.error("test_lcm run raised: %s" % exc)
        if os.path.isfile(log):
            with open(log, "r", encoding="utf-8", errors="ignore") as f:
                txt = f.read()
            # Deterministic count source: each passing check emits one CHECK-OK line.
            for line in txt.splitlines():
                if line.startswith("CHECK-OK:"):
                    passed += 1
        passed_ok = (passed == discovered)
        tp_result = {
            "executed": True,
            "passed": passed_ok,
            "command": "./test_lcm",
            "discovered": discovered,
            "passedCount": passed,
        }
        tp_marker = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_result)
        print(tp_marker, flush=True)
        self.output.info(tp_marker)
        # Re-emit upstream evidence persisted in package res/ so every preflight
        # round carries non-zero upstream proof even on a cache hit.
        self._reemit_upstream()
        if not passed_ok:
            tail = ""
            if os.path.isfile(log):
                with open(log, "r", encoding="utf-8", errors="ignore") as f:
                    tail = f.read()[-4000:]
            self.output.error("test_lcm failed; log tail:\n%s" % tail)
            raise ConanException(
                "test_lcm failed: discovered=%d passed=%d" % (discovered, passed)
            )

    def _reemit_upstream(self):
        try:
            emitted = False
            try:
                dep = self.dependencies[self.tested_reference_str.split("/")[0]]
                cand = os.path.join(dep.package_folder, "res", "upstream_test_result.json")
                if os.path.isfile(cand):
                    with open(cand, "r", encoding="utf-8") as handle:
                        up = json.load(handle)
                    up_marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
                        up, ensure_ascii=False
                    )
                    print(up_marker, flush=True)
                    self.output.info(up_marker)
                    emitted = True
            except Exception as exc:  # noqa: BLE001
                self.output.warning("upstream re-emit lookup failed: %s" % exc)
            if not emitted:
                self.output.warning(
                    "upstream_test_result.json absent from package res/; "
                    "upstream marker left to the main build (cache-miss rounds)"
                )
        except Exception as exc:  # noqa: BLE001
            self.output.warning("upstream re-emit failed: %s" % exc)
