#!/usr/bin/env python3
"""Consumer tests for termbox2 2.5.0.

The upstream test suite (tests/test_*/test.php, 16 cases in v2.5.0) is a
PHP-FFI + X11 (Xvfb/xterm/xvkbd) screen-capture harness that does not exist on
headless OHOS/aarch64. Each upstream case's real logic is a sequence of
termbox2 C API calls against the library, so we port all 16 cases to native C
(``test_<name>.c``, driven over a PTY via tb_init_fd) and execute
them here on the target. They emit real per-case pass/fail and are counted as
the upstream suite.

In addition, two OHOS-specific consumer tests (``test_api.c`` and
``test_ohos_pty.c``) exercise the installed package end to end and are counted
as the test_package suite.

Both suites emit the HMBS_TEST_PACKAGE_RESULT / HMBS_UPSTREAM_TEST_RESULT
machine-evidence markers the preflight gate requires.

Build strategy: the library is a plain GNU Make build driven with the toolchain
clang via ``tools.build:compiler_executables`` (no CMake). The consumer and
ported-upstream test binaries are therefore compiled and linked with that same
toolchain clang directly (mirroring the library build), linking the installed
static lib and the packaged (TB_LIB_OPTS) headers, avoiding the CMakeToolchain
OHOS compiler-detection probe that can mis-detect a bare clang as a broken C
compiler.
"""

import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run

# Upstream test cases in tests/test_*/test.php (v2.5.0): each is ported to a
# native C test that drives the same real termbox2 API over a PTY.
UPSTREAM_SOURCES = (
    # name matches the upstream tests/test_<name> directory
    "test_basic.c",
    "test_64bit.c",
    "test_color_8bit.c",
    "test_color_true.c",
    "test_egc.c",
    "test_error.c",
    "test_invalid_term.c",
    "test_invalid_utf8.c",
    "test_invalidate.c",
    "test_large_input.c",
    "test_mod.c",
    "test_non_printable.c",
    "test_non_spacing_mark.c",
    "test_output_mode.c",
    "test_print.c",
    "test_resize.c",
)
UPSTREAM_DISCOVERED = len(UPSTREAM_SOURCES)

# Consumer test_package cases: one per test executable (OHOS-specific).
TP_SOURCES = ("test_api.c", "test_ohos_pty.c")
TP_DISCOVERED = len(TP_SOURCES)

_ALL_SOURCES = TP_SOURCES + UPSTREAM_SOURCES


class Termbox2TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compiler_executables.get("c", "clang")
        dep = self.dependencies["termbox2"]
        include_dir = os.path.join(dep.package_folder, "include")
        lib_static = os.path.join(dep.package_folder, "lib", "libtermbox2.a")

        bindir = self.build_folder
        os.makedirs(bindir, exist_ok=True)
        for src in _ALL_SOURCES:
            out = os.path.join(bindir, os.path.splitext(src)[0])
            self.run(
                '{cc} -I"{inc}" "{src}" "{lib}" -o "{out}"'.format(
                    cc=cc,
                    inc=include_dir,
                    src=os.path.join(self.source_folder, src),
                    lib=lib_static,
                    out=out,
                ),
            )

    def test(self):
        if not can_run(self):
            self.output.warning(
                "Cross-built tests require execution on a HarmonyOS device"
            )
            return

        bindir = self.build_folder
        executables = {
            os.path.splitext(src)[0]: os.path.join(bindir,
                                                   os.path.splitext(src)[0])
            for src in _ALL_SOURCES
        }
        if str(self.settings.os) == "OHOS":
            for exe in executables.values():
                if os.path.isfile(exe):
                    self._sign_ohos_elf(exe)

        # --- test_package (consumer) suite --------------------------------
        # Each consumer test prints "PASS (N assertions)" and exits 0 only when
        # every assertion holds; self.run raises on a non-zero exit.
        passed_tp = 0
        failures_tp = []
        for src in TP_SOURCES:
            exe = executables[os.path.splitext(src)[0]]
            try:
                self.run(exe, env="conanrun")
                passed_tp += 1
            except Exception as exc:  # noqa: BLE001 - evidence only
                failures_tp.append("%s: %s" % (exe, exc))
        tp_result = {
            "executed": True,
            "passed": passed_tp == TP_DISCOVERED,
            "command": "./test_api && ./test_ohos_pty",
            "discovered": TP_DISCOVERED,
            "passedCount": passed_tp,
        }
        tp_marker = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_result)
        print(tp_marker, flush=True)
        self.output.info(tp_marker)

        # --- upstream suite (16 ported cases actually executed) -----------
        passed = 0
        failed = 0
        failed_names = []
        for src in UPSTREAM_SOURCES:
            exe = executables[os.path.splitext(src)[0]]
            rc = subprocess.run(
                [exe], env=os.environ.copy(), timeout=60
            ).returncode
            if rc == 0:
                passed += 1
            else:
                failed += 1
                failed_names.append(os.path.splitext(src)[0])

        # Deterministic identity checks on the emitted counts.
        assert passed + failed == UPSTREAM_DISCOVERED, (
            "upstream count mismatch: %d+%d != %d"
            % (passed, failed, UPSTREAM_DISCOVERED)
        )

        up_result = {
            "status": "passed" if failed == 0 else "failed",
            "framework": "native C ports of upstream tests/test_*/test.php",
            "command": " ".join(
                "./%s" % os.path.splitext(s)[0] for s in UPSTREAM_SOURCES
            ),
            "discovered": UPSTREAM_DISCOVERED,
            "executed": UPSTREAM_DISCOVERED,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
            "reason": (
                "The 16 upstream tests/test_*/test.php cases are PHP-FFI + X11 "
                "(Xvfb/xterm/xvkbd) screen-capture programs. On headless "
                "OHOS/aarch64 that toolchain is unavailable, so each case is "
                "ported to a native C program (test_package/test_<name>.c) "
                "that drives the same real termbox2 C API over a PTY "
                "(tb_init_fd) and is executed on the target; "
                "%d/%d executed upstream cases passed."
                % (passed, UPSTREAM_DISCOVERED)
            ),
        }
        if failed != 0:
            up_result["gaps"] = [{
                "count": failed,
                "category": "test_failure",
                "detail": (
                    "ported upstream cases that failed on the target: %s"
                    % ", ".join(failed_names)
                ),
                "evidence": (
                    "non-zero exit of the corresponding test_<name> binary "
                    "during preflight"
                ),
            }]
        up_marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
            up_result, ensure_ascii=False
        )
        print(up_marker, flush=True)
        self.output.info(up_marker)

        if passed_tp != TP_DISCOVERED:
            raise ConanException(
                "test_package consumer tests failed: %s"
                % "; ".join(failures_tp)
            )
        # Any upstream failure is reported via the marker/gaps; fail the
        # package test only when a consumer test fails, so the true upstream
        # numbers are what gate the result.
        if failed != 0:
            self.output.warning(
                "upstream ported tests failed: %s" % ", ".join(failed_names)
            )

    @staticmethod
    def _sign_ohos_elf(path):
        if not os.path.isfile(path):
            raise ConanException(f"Missing OHOS test executable: {path}")
        signer = shutil.which("binary-sign-tool") or (
            "/data/service/hnp/bin/binary-sign-tool"
        )
        objcopy = shutil.which("llvm-objcopy") or (
            "/data/service/hnp/bin/llvm-objcopy"
        )
        if not os.path.isfile(signer) or not os.path.isfile(objcopy):
            raise ConanException("Required OHOS signing tools are missing")
        subprocess.run(
            [objcopy, "--remove-section", ".codesign", path],
            check=True,
            timeout=30,
        )
        subprocess.run(
            [
                signer,
                "sign",
                "-inFile",
                path,
                "-outFile",
                path,
                "-selfSign",
                "1",
            ],
            check=True,
            timeout=60,
        )
        os.chmod(path, (os.stat(path).st_mode & 0o777) | 0o055)
