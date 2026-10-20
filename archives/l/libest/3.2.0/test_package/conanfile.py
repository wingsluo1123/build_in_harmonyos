#!/usr/bin/env python3
"""Conan test_package — libest 3.2.0 consumer test (Conan L1)."""

import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class LibestTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # OHOS true-machine fix (earcut/3.2.3 + easyloggingpp/9.97.1
        # precedent): conan maps os=OHOS to CMAKE_SYSTEM_NAME=HarmonyOS,
        # but the preflight cmake (stock 4.4.3) ships no
        # Platform/HarmonyOS module, so project() dies with
        # "System is unknown to cmake" + CMAKE_C_COMPILER sanity failure.
        # HarmonyOS shares the Linux kernel; aliasing to Linux reuses the
        # upstream platform module with identical behaviour for this plain
        # C consumer (no platform branches in test CMakeLists).
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            try:
                tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(
                    self.settings.arch)
            except Exception:
                tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "armv8"
        # Stale profile compiler fix (zydis/4.1.1 precedent): the shared
        # profile pins tools.build:compiler_executables to
        # /data/service/hnp/bin/clang, absent on some HMBS hosts. Pin the
        # resolved compiler only when the configured path is missing and a
        # working one exists (CI workers with a valid path untouched).
        try:
            _compilers = self.conf.get("tools.build:compiler_executables",
                                       default=None)
        except Exception:
            _compilers = None
        if not isinstance(_compilers, dict):
            _compilers = {}
        _c = self._resolve_compiler(_compilers.get("c"),
                                    ("clang", "cc", "gcc"))
        _cxx = self._resolve_compiler(_compilers.get("cpp"),
                                      ("clang++", "c++", "g++"))
        if _c:
            tc.cache_variables["CMAKE_C_COMPILER"] = _c
        if _cxx:
            tc.cache_variables["CMAKE_CXX_COMPILER"] = _cxx
        self.output.info(f"libest test_package compilers c={_c} cxx={_cxx}")
        tc.generate()
        # Export CC/CXX in build scope when we overrode a stale path, so
        # CMake's compiler probe (which honours env) agrees with the cache.
        try:
            c_old = _compilers.get("c")
            cxx_old = _compilers.get("cpp")
            env = Environment()
            if c_old and _c and c_old != _c \
                    and not os.path.exists(c_old) and os.path.exists(_c):
                env.define("CC", _c)
            if cxx_old and _cxx and cxx_old != _cxx \
                    and not os.path.exists(cxx_old) and os.path.exists(_cxx):
                env.define("CXX", _cxx)
            env.vars(self, scope="build").save_sh("libest_test_compiler")
        except Exception as e:
            self.output.warning(f"libest test compiler env failed: {e}")
        self._fix_generated_toolchain_compiler(_compilers, _c, _cxx)

    def _resolve_compiler(self, configured, names):
        # Prefer the profile value when it exists (CI worker unchanged);
        # otherwise resolve via PATH plus known true-machine SDK dirs.
        # Pure isfile probing, no X_OK probing per R49.
        def _ok(p):
            try:
                return bool(p) and os.path.isfile(p)
            except Exception:
                return False
        if configured and _ok(configured):
            return configured
        for name in names:
            try:
                found = shutil.which(name)
            except Exception:
                found = None
            if found and _ok(found):
                return found
        cand_dirs = [
            "/storage/Users/currentUser/usr/local/bin",
            os.path.join(os.path.expanduser("~"), ".harmonybrew", "bin"),
            "/data/service/hnp/bin",
            "/opt/llvm/bin",
            "/usr/local/bin",
            "/usr/bin",
        ]
        for d in cand_dirs:
            try:
                if not os.path.isdir(d):
                    continue
            except Exception:
                continue
            for n in names:
                p = os.path.join(d, n)
                if _ok(p):
                    return p
        return configured or names[0]

    def _fix_generated_toolchain_compiler(self, configured_map, c, cxx):
        # Mirror zydis/4.1.1: the cache_variables pin alone did not
        # override the stale profile compiler on one true device generation,
        # so correct the generated conan_toolchain.cmake text itself -- only
        # when the configured path is missing and the resolved one exists.
        if not isinstance(configured_map, dict):
            configured_map = {}
        c_old = configured_map.get("c")
        cxx_old = configured_map.get("cpp")
        pairs = []
        try:
            if c_old and c and c_old != c \
                    and not os.path.exists(c_old) and os.path.exists(c):
                pairs.append((c_old, c))
            if cxx_old and cxx and cxx_old != cxx \
                    and not os.path.exists(cxx_old) and os.path.exists(cxx):
                pairs.append((cxx_old, cxx))
        except Exception:
            return
        if not pairs:
            return
        try:
            gf = getattr(self, "generators_folder", None)
            path = os.path.join(gf, "conan_toolchain.cmake") if gf else None
            if path and os.path.isfile(path):
                with open(path, "r", encoding="utf-8",
                          errors="replace") as f:
                    text = f.read()
                orig = text
                for old_p, new_p in pairs:
                    text = text.replace(old_p, new_p)
                if text != orig:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(text)
                    self.output.info(
                        f"libest test fixed toolchain {path}")
        except Exception as e:
            self.output.warning(
                f"libest test toolchain fix failed: {e}")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Consumer test: ctest entry (test_libest) exercising 3 real
        # libest APIs (est_get_version/est_get_api_level/est_init_logger).
        # Deterministic counting (no string-count arithmetic, no
        # returncode-guess patches):
        # - discovered from `ctest -N` (Total Tests: N), redirected to a
        #   file so the evidence does not depend on Conan stdout capture;
        # - verdicts from the ctest stdout file (`Test #N ... Passed|Failed`)
        #   as the single source; Testing/Temporary/LastTest.log
        #   (`Test Passed.`/`Test Failed.` lines) is used ONLY when stdout
        #   carries zero verdict lines (single-source fallback, never both
        #   mixed, never findall-minus arithmetic).
        build_dir = self.build_folder
        ctest_stdout_log = os.path.join(build_dir, "hmbs_ctest_output.log")
        ctest_n_log = os.path.join(build_dir, "hmbs_ctest_N.log")
        last_log = os.path.join(
            build_dir, "Testing", "Temporary", "LastTest.log")
        searched = [ctest_stdout_log, ctest_n_log, last_log]
        discovered = 1
        try:
            try:
                self.run(f'ctest -N > "{ctest_n_log}" 2>&1',
                         cwd=build_dir, env="conanrun")
            except Exception:
                pass
            if os.path.isfile(ctest_n_log):
                with open(ctest_n_log, "r", encoding="utf-8",
                          errors="replace") as f:
                    n_text = f.read()
                m = re.search(r"Total Tests:\s*(\d+)", n_text)
                if m:
                    discovered = int(m.group(1))
        except Exception as exc:
            self.output.warning(f"ctest -N parse failed: {exc}")
        ctest_ok = False
        ctest_out = ""
        try:
            # Redirect to a file: deterministic log source + keeps the
            # preflight log human-readable via the tail echo below.
            self.run(f'ctest --output-on-failure > "{ctest_stdout_log}" 2>&1',
                     cwd=build_dir, env="conanrun")
            ctest_ok = True
        except Exception as exc:
            self.output.warning(f"ctest run failed (will parse logs): {exc}")
            ctest_ok = False
        # Echo the captured ctest output tail so the preflight log keeps
        # human evidence; counting below reads the same files.
        try:
            if os.path.isfile(ctest_stdout_log):
                with open(ctest_stdout_log, "r", encoding="utf-8",
                          errors="replace") as f:
                    ctest_out = f.read()
                self.output.info("ctest output tail:\n" + ctest_out[-4000:])
        except Exception as exc:
            self.output.warning(f"ctest output read failed: {exc}")
        # Verdicts: stdout `Test #N ... Passed|Failed|Timeout` lines are the
        # single source. Each test number maps to exactly one verdict; the
        # last verdict for a number wins (no cross-source mixing).
        verdict_by_test = {}
        try:
            for line in ctest_out.splitlines():
                m = re.search(
                    r"Test\s+#(\d+)[^:]*:.*?(\bPassed\b|\bFailed\b|\bTimeout\b)",
                    line)
                if m:
                    verdict_by_test[int(m.group(1))] = m.group(2)
        except Exception as exc:
            self.output.warning(f"ctest stdout parse failed: {exc}")
        passed_count = 0
        failed_count = 0
        executed = 0
        source_used = "ctest-stdout"
        if verdict_by_test:
            executed = len(verdict_by_test)
            for _v in verdict_by_test.values():
                if _v == "Passed":
                    passed_count += 1
                else:
                    failed_count += 1
        else:
            # Single-source fallback: stdout carried zero verdict lines, so
            # read LastTest.log (`Test Passed.`/`Test Failed.`/`Test Timeout.`
            # one line per test section). Used ONLY in this branch.
            source_used = "LastTest.log"
            try:
                if os.path.isfile(last_log):
                    with open(last_log, "r", encoding="utf-8",
                              errors="replace") as f:
                        last_text = f.read()
                    for line in last_text.splitlines():
                        s = line.strip()
                        if s == "Test Passed.":
                            passed_count += 1
                            executed += 1
                        elif s in ("Test Failed.", "Test Timeout."):
                            failed_count += 1
                            executed += 1
                    if executed == 0:
                        self.output.warning(
                            "ctest stdout has no verdict lines and "
                            f"LastTest.log has no Test Passed./Failed. lines; "
                            f"searched={searched}")
                else:
                    self.output.warning(
                        f"ctest stdout has no verdict lines and LastTest.log "
                        f"not found; searched={searched}")
            except Exception as exc:
                self.output.warning(f"LastTest.log parse failed: {exc}")
        self.output.info(
            f"libest test_package counts source={source_used} "
            f"discovered={discovered} executed={executed} "
            f"passed={passed_count} failed={failed_count} ctest_ok={ctest_ok}")
        # Deterministic identities: passed+failed==executed,
        # executed<=discovered. Numbers have a single source each
        # (no cross-source mixing, no returncode-guess patch).
        try:
            assert isinstance(discovered, int) and discovered >= 0
            assert isinstance(passed_count, int) and passed_count >= 0
            assert isinstance(failed_count, int) and failed_count >= 0
            assert isinstance(executed, int) and executed >= 0
            assert passed_count + failed_count == executed
            assert executed <= discovered
        except AssertionError:
            self.output.warning(
                f"test_package count identity violated: discovered={discovered} "
                f"executed={executed} passed={passed_count} failed={failed_count}")

        tp_passed = (passed_count == discovered and discovered > 0
                     and executed == discovered and failed_count == 0)
        tp_result = {
            "executed": True,
            "passed": tp_passed,
            "command": "ctest --output-on-failure (test_libest: "
                       "est_get_version/est_get_api_level/est_init_logger)",
            "discovered": discovered,
            "passedCount": passed_count,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_result))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_result),
              flush=True)

        # Upstream evidence: the main recipe build() compiles test/UT/runtest
        # (55 CUnit suites, cunit+curl test requirements) and persists the
        # real run counts to package res/hmbs_upstream.json. Re-emit that
        # file here so every preflight round (including cache-hit rounds
        # that skip the main build) carries non-zero upstream evidence.
        # Never fabricate: if the file is absent, emit an honest failed
        # marker with the search path (no skipped-with-environment-gap,
        # no no_tests).
        upstream_tests_total = 55
        ut_emitted = False
        try:
            try:
                dep = self.dependencies[self.tested_reference_str.split("/")[0]]
                cand = os.path.join(
                    dep.package_folder, "res", "hmbs_upstream.json")
                if os.path.isfile(cand):
                    with open(cand, "r", encoding="utf-8") as handle:
                        ut_result = json.load(handle)
                    self.output.info(
                        "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(ut_result))
                    print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(ut_result),
                          flush=True)
                    ut_emitted = True
                else:
                    self.output.warning(
                        "hmbs_upstream.json absent in package res/; "
                        f"searched=[{cand}]")
            except Exception as exc:
                self.output.warning(f"upstream re-emit lookup failed: {exc}")
        except Exception as exc:
            self.output.warning(f"upstream re-emit failed: {exc}")
        if not ut_emitted:
            ut_result = {
                "status": "failed",
                "framework": "cunit",
                "command": "test/UT/runtest (55 CUnit suites)",
                "discovered": upstream_tests_total,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": upstream_tests_total,
                "reason": (
                    "package res/hmbs_upstream.json absent; main recipe "
                    "build() did not persist upstream evidence "
                    "(cache-hit on an old package or upstream build failed "
                    "before persisting). See build log for the runtest "
                    "evidence."),
                "gaps": [
                    {
                        "count": upstream_tests_total,
                        "category": "test_failure",
                        "detail": (
                            "upstream evidence file missing in package; "
                            "no test executed in this round"),
                        "evidence": (
                            "searched package res/hmbs_upstream.json; "
                            "absent"),
                    }
                ],
            }
            self.output.info(
                "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(ut_result))
            print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(ut_result),
                  flush=True)

        if not tp_passed:
            raise ConanException(
                f"test_package checks failed: {tp_result} "
                f"(log searched: {searched})")
