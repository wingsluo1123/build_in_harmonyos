#!/usr/bin/env python3
"""Conan test_package — xdffileio 0.3 (consumer view).

Two consumer tests link the packaged library and really exercise it:

* ``test_xdffileio_api`` — BDF round-trip through the public xdfio.h API
  (open/write/close/reopen/read + get_conf channel count, 14 CHECKs);
* ``test_xdffileio_ohos`` — HarmonyOS-specific checks (writable TMPDIR data
  round-trip + pkg-config + 6 CHECKs).

Both binaries print CHECK PASS/FAIL lines and TEST PASS/FAIL footers; this
recipe counts real process exit codes (deterministic, no stdout word
counting) and emits HMBS_TEST_PACKAGE_RESULT. It also re-emits the upstream
``make check`` evidence persisted by build() so cached runs keep it.
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


class XdffileioTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _compiler_executable(self, key, fallback_name):
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
            "/data/service/hnp/bin/clang++": self._compiler_executable("cpp", "clang++"),
            "/data/service/hnp/bin/clang": self._compiler_executable("c", "clang"),
        }
        for old, new in replacements.items():
            replace_in_file(self, toolchain, old, new, strict=False)

    def generate(self):
        # Stale-toolchain guard (cvector/1.0.4.1 precedent): the repo profile
        # pins /data/service/hnp/bin/clang(++), but that file may not exist
        # on the current preflight worker (test package cmake.configure then
        # dies with "CMAKE_C_COMPILER: /data/service/hnp/bin/clang ... not
        # found"). Resolve to an existing binary and force it via cache
        # variables + post-generate toolchain patch. Healthy machines keep
        # the configured value (existence check first, zero change there).
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        if str(self.settings.get_safe("os")) == "OHOS":
            tc.cache_variables["CMAKE_C_COMPILER"] = self._compiler_executable("c", "clang")
            tc.cache_variables["CMAKE_CXX_COMPILER"] = self._compiler_executable("cpp", "clang++")
        tc.generate()
        if str(self.settings.get_safe("os")) == "OHOS":
            self._patch_cmake_toolchain_compilers()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: xdffileio consumer tests skipped")
            return
        bindir = self.cpp.build.bindirs[0]
        cases = ["test_xdffileio_api", "test_xdffileio_ohos"]
        passed = 0
        for case in cases:
            exe = os.path.join(bindir, case)
            self.run('"%s"' % exe, env="conanrun")
            passed += 1
        marker = {
            "executed": True,
            "passed": passed == len(cases),
            "command": "ctest --output-on-failure + %s" % " + ".join(cases),
            "discovered": len(cases),
            "passedCount": passed,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        dep = self.dependencies[self.tested_reference_str]
        result_path = os.path.join(dep.package_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(result_path):
            raise ConanException(
                "upstream_test_result.json not found in package (%s); "
                "upstream tests did not run during build()" % result_path
            )
        with open(result_path, "r", encoding="utf-8") as f:
            upstream = json.load(f)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream))
