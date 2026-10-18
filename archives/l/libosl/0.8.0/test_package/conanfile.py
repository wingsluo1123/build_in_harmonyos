#!/usr/bin/env python3
"""Consumer test for libosl 0.8.0 — exercises the real public C++ API.

Builds test_osl.cpp (Move/Square API, CSA initial-state parsing and
NumEffectState consistency, aarch64 platform configuration) with CMake and
runs the three ctest cases via the repo-blessed `self.run(bash -c ctest)`
pattern (debugbreak/racon precedent: /system/bin/sh cannot exec ELF
directly). Counts come from deterministic framework sources only —
`ctest -N` for discovered, Testing/Temporary/LastTest.log per-case lines
for passed/failed — never from stdout substring arithmetic.
"""
import json
import os
import re
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LiboslTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # Conan 2: CMakeToolchain is customized in generate(), so it must NOT
    # also appear in `generators` (declaring it in both places raises
    # "CMakeToolchain is declared in the generators attribute, but was
    # instantiated in the generate() method too"). Keep only CMakeDeps here.
    generators = "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # Same standard as the library build (main recipe -std=c++14):        # Boost 1.84 needs >=C++14, while upstream public headers predate
        # C++17 removals, so a consumer at C++17 risks hard errors.
        tc.cache_variables["CMAKE_CXX_STANDARD"] = "14"
        tc.cache_variables["CMAKE_CXX_STANDARD_REQUIRED"] = True
        # osl public headers pull Boost smart_ptr headers; the Boost 1.84
        # sp_thread_sleep.hpp guard needs this macro on OHOS musl (no
        # pthread_setcancelstate). package_info() also propagates it via
        # CMakeDeps; belt-and-suspenders here covers direct TU compiles.
        tc.preprocessor_definitions["BOOST_SP_NO_PTHREAD_SETCANCELSTATE"] = "1"
        # osl public headers include Boost headers (e.g. construct.h ->
        # boost/type_traits/has_trivial_destructor.hpp), but the split
        # boost1.84-* component packages all claim cmake_file_name "Boost",
        # so CMakeDeps cannot reliably propagate their includes through
        # libosl::libosl alone (true-machine: test_osl.cpp.o fatal error).
        # Inject the transitive Boost include dirs directly as compiler
        # flags; every component ships the same Boost 1.84.0 headers, so any
        # available one suffices. No test logic changed.
        for _ref in ("boost1.84-serialization", "boost1.84-iostreams",
                     "boost1.84-system", "boost1.84-date_time",
                     "boost1.84-filesystem"):
            try:
                _pkg = self.dependencies[_ref]
            except KeyError:
                continue
            _inc = os.path.join(_pkg.package_folder, "include")
            if os.path.isdir(_inc):
                tc.extra_cxxflags.append(f"-I{_inc}")
        if self.settings.os in ("Linux", "OHOS"):
            # Keep CMake's platform logic usable with the OHOS Conan profile.
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def _ctest_discovered(self, bash):
        """Deterministic total from `ctest -N` (single source)."""
        try:
            proc = subprocess.run(
                [bash, "-c", "ctest -N"],
                cwd=self.build_folder,
                capture_output=True,
                text=True,
                timeout=120,
            )
            m = re.search(r"Total Tests:\s*(\d+)", proc.stdout or "")
            if m:
                return int(m.group(1))
        except Exception as exc:
            self.output.warning(f"ctest -N probe failed: {exc}")
        return None

    def _parse_last_test_log(self):
        """Per-case passed/failed from LastTest.log status lines.

        Single deterministic source: CTest writes one `Test Passed.` /
        `Test Failed.` / `Test Timeout.` status line per test into
        Testing/Temporary/LastTest.log (multi-line format: `Test #N:` and
        the status line are on DIFFERENT lines, so a same-line
        `Test #N ... Passed` regex always yields 0 -- mathic/1.4 precedent).
        Picks the newest LastTest.log under the build folder to avoid a
        stale log, and logs path+tail for diagnostics.
        """
        candidates = []
        for root, _dirs, files in os.walk(self.build_folder):
            if "LastTest.log" in files:
                candidates.append(os.path.join(root, "LastTest.log"))
        if not candidates:
            searched = []
            for root, _dirs, _files in os.walk(self.build_folder):
                searched.append(root)
                if len(searched) >= 5:
                    break
            raise RuntimeError(
                "LastTest.log not found; searched: "
                + ", ".join(searched)
            )
        log_path = max(candidates, key=lambda p: os.path.getmtime(p))
        with open(log_path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        # Strip ANSI escapes first (same as upstream parser).
        text = re.sub(r"\x1b\[[0-9;]*m", "", text)
        passed = text.count("Test Passed.")
        failed = text.count("Test Failed.") + text.count("Test Timeout.")
        self.output.info(
            f"LastTest.log: {log_path} passed={passed} failed={failed}"
        )
        tail = text[-2000:] if len(text) > 2000 else text
        self.output.info(f"LastTest.log tail:\n{tail}")
        return passed, failed

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries directly,
        # so run ctest through the bash from the build environment.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        if not (os.path.isfile(bash) and os.access(bash, os.X_OK)):
            bash = "/bin/sh"
        discovered = self._ctest_discovered(bash)
        if discovered is None:
            marker = {
                "executed": True,
                "passed": False,
                "command": "ctest -N",
                "discovered": 0,
                "passedCount": 0,
                "reason": "ctest -N produced no Total Tests line",
            }
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker)
            )
            raise RuntimeError(marker["reason"])
        command = "ctest --output-on-failure"
        try:
            self.run(f'{bash} -c "ctest --output-on-failure"',
                      cwd=self.build_folder, env="conanrun")
        except Exception:
            passed_count, _failed = 0, 0
            reason = "ctest exited non-zero"
            try:
                passed_count, failed = self._parse_last_test_log()
                reason += f"; LastTest.log passed={passed_count} failed={failed}"
            except Exception as exc:
                reason += f"; log parse failed: {exc}"
            marker = {
                "executed": True,
                "passed": False,
                "command": command,
                "discovered": discovered,
                "passedCount": passed_count,
                "reason": reason,
            }
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker)
            )
            raise
        passed_count, failed_count = self._parse_last_test_log()
        ok = (
            failed_count == 0
            and passed_count == discovered
            and passed_count + failed_count == discovered
        )
        marker = {
            "executed": True,
            "passed": ok,
            "command": command,
            "discovered": discovered,
            "passedCount": passed_count,
        }
        if not ok:
            marker["reason"] = (
                f"LastTest.log passed={passed_count} "
                f"failed={failed_count} discovered={discovered}"
            )
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker)
        )
        if not ok:
            raise RuntimeError(marker["reason"])
