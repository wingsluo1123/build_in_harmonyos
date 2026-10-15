#!/usr/bin/env python3
"""Conan recipe: kati/0_git20251208 (Google kati — GNU make clone, ckati)

OHOS adaptation notes (see notes.md for full rationale):
- Upstream is a plain-Makefile C++17 build (Makefile.ckati, 26 src/*.cc).
  Zero external dependencies. The Rust rewrite (src-rs/rkati) and the Go
  test harness (run_test.go) are NOT in the default build path and are
  ignored by this recipe.
- KATI_CXXFLAGS is overridden on the command line to drop `-march=native`
  (OHOS aarch64 clang does not reliably support it) while keeping the
  upstream -MMD -MP dep-file flags and -DNOLOG.
- The source tarball has no .git dir -> Makefile.ckati falls back to
  KATI_VERSION := "unknown" for version.cc (verified against upstream
  Makefile.ckati logic); nothing to do.
- Upstream tests, ported faithfully (no Go on OHOS):
    1) 3 C++ unit test exes (find_test/ninja_test/strutil_test) built by
       `make all`'s ckati_tests target; run hard-fail in build().
    2) the 296-testcase differential suite (testcase/*.mk): upstream runs
       it via `go test` (run_test.go) comparing GNU make vs ckati output.
       OHOS has no Go, so tests/run_testcases.py is a faithful Python
       port of the same harness (same invocation flags, same output
       normalization regexes, same file-list comparison, same # TODO
       xfail semantics). GNU make is present on the build host (it builds
       ckati itself). Hard-fails on unexpected mismatches; known platform
       xfails are pinned in tests/xfail.txt with reasons.
- R38: software-level commands.json required (ckati executable).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class KatiConan(ConanFile):
    name = "kati"
    version = "0_git20251208"
    description = "Google kati: GNU make clone with --ninja support (ckati)"
    homepage = "https://github.com/google/kati"
    license = "Apache-2.0"
    url = ""
    topics = ("make", "build", "android", "cli")

    settings = "os", "arch", "compiler", "build_type"
    package_type = "application"
    # Delivered product is the ckati executable; no headers/libs.
    # R38 commands.json required (CLI tool artifact).
    # tests/ = the ported differential harness (run_testcases.py) + the
    # platform-xfail pin file; must be exported as SOURCES (not just recipe
    # exports) so they land in the build tree where build() runs them.
    exports_sources = "tests/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # zero external dependencies (W0)

    def layout(self):
        basic_layout(self)

    def source(self):
        # conandata.yml keys sources by version; index explicitly.
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: compiler paths come from Conan conf, never from env vars.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = compilers.get("cpp") or "clang++"

        # Upstream KATI_CXXFLAGS := "-g -W -Wall -MMD -MP -O -DNOLOG
        # -march=native". Command-line assignment overrides; we drop
        # -march=native (aarch64 OHOS clang) and trim -g. -std=c++17 is
        # added by the upstream rules themselves, not via CXXFLAGS.
        kati_cxxflags = "-O2 -g0 -W -Wall -MMD -MP -DNOLOG"

        # R9: -j1. `all` = ckati + ckati_tests (3 unit test exes).
        self.run(
            'make all CXX="{}" KATI_CXXFLAGS="{}" -j1'.format(cxx, kati_cxxflags),
            cwd=self.source_folder,
        )

        self._run_unit_tests()
        self._run_differential_suite()

    def _run_unit_tests(self):
        # ckati_tests target builds find_test / ninja_test / strutil_test
        # (custom testutil.h harness, deterministic). *_bench exes are
        # also built but not run (benchmarks, not tests).
        if self.conf.get("tools.build:skip_test", default=False):
            self.output.info("tools.build:skip_test -> skip kati tests")
            return
        src = self.source_folder
        for t in ("find_test", "ninja_test", "strutil_test"):
            self.run(os.path.join(".", t), cwd=src)

    def _run_differential_suite(self):
        if self.conf.get("tools.build:skip_test", default=False):
            self.output.info("tools.build:skip_test -> skip differential suite")
            return
        # Python port of run_test.go's .mk differential harness (same
        # normalizations/invocation); see tests/run_testcases.py.
        # SHELL: OHOS has no /bin/bash; the harness passes SHELL=<bash>
        # exactly like upstream passes SHELL=/bin/bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # python3 on OHOS lives outside the HNP tree (observed 3.12.9 at
        # /storage/Users/currentUser/usr/local/bin/python3); PYTHON wins,
        # then PATH, then the known device path.
        python = (os.environ.get("PYTHON") or shutil.which("python3")
                  or "/storage/Users/currentUser/usr/local/bin/python3")
        # Sandbox workdir: upstream run_test.go fixes it at <source root>/
        # out/<name>/{make,kati} — the depth is part of the fixture
        # contract (find_command.mk test1 references the source tree as
        # ../../../testcase/tools/...). Keep the exact upstream layout so
        # fixtures resolve. Also: device /tmp is a read-only mount (ivar
        # precedent, EROFS), so the harness must NOT rely on
        # tempfile.gettempdir().
        workdir = os.path.join(self.source_folder, "out")
        os.makedirs(workdir, exist_ok=True)
        self.run(
            '{} "{}" --ckati ./ckati --shell "{}" '
            '--workdir "{}" --xfail-file "{}"'.format(
                python, os.path.join("tests", "run_testcases.py"), bash,
                workdir, os.path.join("tests", "xfail.txt")),
            cwd=self.source_folder,
        )

    def package(self):
        src = self.source_folder
        pkg = self.package_folder
        copy(self, "ckati", src, os.path.join(pkg, "bin"))
        copy(self, "AUTHORS", src, os.path.join(pkg, "licenses"))
        copy(self, "LICENSE", src, os.path.join(pkg, "licenses"))
        copy(self, "NOTICE", src, os.path.join(pkg, "licenses"))

    def package_info(self):
        # Application package: delivered product is bin/ckati.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
