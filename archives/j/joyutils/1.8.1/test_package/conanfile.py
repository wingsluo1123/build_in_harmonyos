#!/usr/bin/env python3
"""Conan test_package for joyutils 1.8.1 (command-line tool).

joyutils is a tool package (bin/jstest, bin/jscal, ...), so build()
does no library linking; test() executes test_joyutils.sh against the
installed binaries for 4 hardware-free checks (jstest --help usage,
jscal -h usage, bare jscal usage, missing-device negative control),
satisfying L0d (test() holds self.run) and R34 (packaged binaries are
really executed). test() runs with env="conanrun" plus inline
JSTEST_BIN/JSCAL_BIN/TMPDIR so paths survive env merge semantics.

Evidence markers:
- HMBS_TEST_PACKAGE_RESULT: discovered/passedCount parsed from the real
  "RESULT: P passed, F failed" trailer line of the script output.
- HMBS_UPSTREAM_TEST_RESULT: status=no_tests. Upstream ships no test
  suite (no check/test target in top/utils/docs Makefiles; audit in
  MANIFEST.yml). The marker is re-emitted here because the main-recipe
  build() output may be skipped on cache-hit ("Already installed!")
  preflight rounds.
"""

import json
import os
import re
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.layout import basic_layout


class JoyutilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        # Tool package: no library to link; functional checks run in test().
        pass

    def _writable_signed_copy(self, binary):
        """Copy the packaged binary to writable TMPDIR and self-sign it.

        The conan cache may sit on read-only HMDFS; signing the package
        copy in place fails silently and the HongMeng kernel SIGKILLs
        unsigned binaries on exec. Signing a writable copy avoids that.
        """
        writable_tmp = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or self.build_folder
        )
        try:
            os.makedirs(writable_tmp, exist_ok=True)
        except OSError:
            writable_tmp = self.build_folder
        base = os.path.basename(binary)
        signed_copy = os.path.join(writable_tmp, base + ".signed")
        try:
            shutil.copy2(binary, signed_copy)
            self.output.info(
                "OHOS test: copied %s -> writable %s for signing"
                % (binary, signed_copy)
            )
            binary = signed_copy
        except Exception as exc:
            self.output.warning(
                "OHOS test: copy to writable tmp failed (%s)" % exc
            )
            return binary
        for tool in (
            "/data/service/hnp/bin/llvm-objcopy",
            shutil.which("llvm-objcopy") or "llvm-objcopy",
        ):
            try:
                subprocess.run(
                    [tool, "--remove-section", ".codesign", binary],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                    timeout=10,
                )
                break
            except Exception:
                continue
        signed = False
        for tool in (
            "/data/service/hnp/bin/binary-sign-tool",
            shutil.which("binary-sign-tool") or "binary-sign-tool",
        ):
            try:
                proc = subprocess.run(
                    [tool, "sign", "-inFile", binary,
                     "-outFile", binary, "-selfSign", "1"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                    timeout=15,
                )
                if proc.returncode == 0:
                    self.output.info(
                        "OHOS self-signed test binary %s with %s"
                        % (binary, tool)
                    )
                    signed = True
                    break
                self.output.warning(
                    "sign tool %s returned %s" % (tool, proc.returncode)
                )
            except Exception as exc:
                self.output.warning("sign tool %s exception: %s" % (tool, exc))
                continue
        if not signed:
            self.output.warning(
                "OHOS signing failed for %s (will try exec anyway)" % binary
            )
        try:
            os.chmod(binary, 0o755)
        except OSError:
            pass
        return binary

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        jstest_bin = os.path.join(pkg, "bin", "jstest")
        jscal_bin = os.path.join(pkg, "bin", "jscal")
        for path in (jstest_bin, jscal_bin):
            if not os.path.isfile(path):
                raise ConanException(
                    "joyutils binary not found in package: %s" % path
                )
        if self.settings.os == "OHOS":
            jstest_bin = self._writable_signed_copy(jstest_bin)
            jscal_bin = self._writable_signed_copy(jscal_bin)

        shell = (
            os.environ.get("CONFIG_SHELL")
            or os.environ.get("SHELL")
            or "/bin/sh"
        )
        tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or os.path.join(self.build_folder, ".tmp")
        )
        os.makedirs(tmpdir, exist_ok=True)

        test_script = os.path.join(self.recipe_folder, "test_joyutils.sh")
        logfile = os.path.join(self.build_folder, "test_package.log")

        inner = "%s %s %s %s %s %s %s > %s 2>&1" % (
            "JSTEST_BIN=%s" % shlex.quote(jstest_bin),
            "JSCAL_BIN=%s" % shlex.quote(jscal_bin),
            "TMPDIR=%s" % shlex.quote(tmpdir),
            "TMP=%s" % shlex.quote(tmpdir),
            "TEMP=%s" % shlex.quote(tmpdir),
            "timeout 90" if (
                shutil.which("timeout")
                or os.path.isfile("/data/service/hnp/bin/timeout")
            ) else "exec",
            shlex.quote(shell) + " " + shlex.quote(test_script),
            shlex.quote(logfile),
        )
        self.run(inner, env="conanrun", ignore_errors=True)

        out = ""
        if os.path.isfile(logfile):
            with open(logfile, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        self.output.info(
            "test_joyutils.sh log:\n" + "\n".join(out.splitlines()[-16:])
        )

        m = re.search(r"RESULT: (\d+) passed, (\d+) failed", out)
        if not m:
            raise ConanException(
                "test_joyutils.sh produced no RESULT line - harness broken"
            )
        passed = int(m.group(1))
        failed = int(m.group(2))
        discovered = passed + failed
        ok = failed == 0 and discovered > 0

        marker = {
            "executed": True,
            "passed": ok,
            "command": "%s test_joyutils.sh (JSTEST_BIN/JSCAL_BIN=<pkg>/bin)" % shell,
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
        if not ok:
            raise ConanException(
                "test_joyutils.sh failed: %d/%d cases failed" % (failed, discovered)
            )

        upstream_marker = {
            "status": "no_tests",
            "framework": "none",
            "command": "none (upstream ships no test suite; see MANIFEST.yml audit)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "linuxconsoletools-1.8.1 has no check/test target; Alpine build log confirms no testsuite",
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker, ensure_ascii=False)
        )
