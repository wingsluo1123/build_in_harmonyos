#!/usr/bin/env python3
"""Conan test_package — mbtserver 0.17 (library + tool).

Consumer checks (3 real executions, fail-fast):
  1. test_mbtserver binary: includes <mbtserver/MbtServerBase.h> and takes
     the addresses of MbtServer::StartServer / MbtServer::StartJSONServer,
     forcing the linker to resolve real libmbtserver symbols (R34: a broken
     library or header set fails the link instead of passing silently).
     Note: the header declares VersionInfo(bool) but upstream never defines
     it, so the test deliberately does not reference it (see MANIFEST.yml).
  2. Packaged bin/mbtserver --help: exits 0 via the code-proven immediate
     exit path (StartServer prints usage() and exits EXIT_SUCCESS); the
     log must contain the "usage:" banner (non-empty-output guard).
  3. Packaged bin/mbtserver --version: exits 0 via the code-proven
     immediate exit path (no server is started, nothing can hang).

All binaries are fully statically linked, so self.run uses env="" (icu/76.1
E064 precedent: sourcing Conan shell wrappers on OHOS once SIGSEGV'd).

Evidence markers:
- HMBS_TEST_PACKAGE_RESULT: discovered/passedCount count the 3 registered
  checks above (single deterministic source, no stdout pattern counting).
- HMBS_UPSTREAM_TEST_RESULT: status=no_tests. Upstream registers no test
  suite (no TESTS/check_PROGRAMS in any Makefile.am; CI runs build +
  cppcheck only; audit in MANIFEST.yml). Re-emitted here because the main
  recipe build() output is skipped on cache-hits ("Already installed!").
"""

import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MbtserverTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Packaged public headers (vendored timbl/ticcutils trees) directly
        # include unicode/unistr.h, libxml headers, zlib.h, bzlib.h, and
        # CMakeDeps does not expand transitive includes for consumers, so
        # each remote dep is declared explicitly (dwarves/1.30 precedent).
        self.requires("icu/76.1")
        self.requires("libxml2/2.15.3")
        self.requires("zlib/1.3.2")
        self.requires("bzip2/1.0.8.2")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_binary = os.path.join(self.cpp.build.bindir, "test_mbtserver")
        mbtserver_bin = os.path.join(
            self.dependencies["mbtserver"].package_folder, "bin", "mbtserver")
        if not os.path.isfile(mbtserver_bin):
            raise ValueError("mbtserver binary not found in package: %s" % mbtserver_bin)
        help_log = os.path.join(self.build_folder, "mbtserver_help.log")

        # 3 registered consumer checks (fail-fast: nonzero exit aborts here,
        # which is the honest failure signal for the preflight round).
        self.run('"%s"' % test_binary, env="")
        self.run('"%s" --help > "%s" 2>&1' % (mbtserver_bin, help_log), env="")
        with open(help_log, "r", encoding="utf-8", errors="replace") as f:
            help_out = f.read()
        if "usage:" not in help_out:
            raise ValueError(
                "mbtserver --help produced no usage banner — vacuous pass rejected")
        self.run('"%s" --version' % mbtserver_bin, env="")

        marker = {
            "executed": True,
            "passed": True,
            "command": "test_mbtserver && mbtserver --help && mbtserver --version",
            "discovered": 3,
            "passedCount": 3,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        upstream_marker = {
            "status": "no_tests",
            "framework": "autotools",
            "command": "make check (upstream registers no tests)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "mbtserver 0.17 上游无自动化测试套件：39 条目源码归档无 tests/test 目录与 *test* 源文件；顶层/src/include/docs/example 的 Makefile.am 均无 TESTS/check_PROGRAMS/check-local 注册；上游 CI (mbtserver.yml) 仅构建 + cppcheck（详见 test_package/MANIFEST.yml 审计）",
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker, ensure_ascii=False))
        self.output.info("mbtserver consumer test_package passed")
