#!/usr/bin/env python3
"""Conan test_package for quex 0.71.2.

Drives the packaged ``quex`` generator end to end via the standalone
test source test_quex.py (CI L0c gate requires a .py/.sh/.c file beside
conanfile.py; assertions inline in test() alone do not satisfy it):

  1. quex --help runs (binary resolved by absolute path, not PATH lookup).
  2. quex --version reports 0.71.2.
  3. (cd TMP && quex -i tiny.qx -o tiny_lexer --language C) generates a lexer tree.
  4. Generated output is non-empty and mentions the declared tokens.

The driver prints one ``CHECK-OK: <name>`` line per check; this conanfile
executes it with self.run() (L0d/R34) redirecting to a log file, then counts
that single deterministic source for the HMBS_TEST_PACKAGE_RESULT marker.
Exit-code-0 alone is never treated as proof.

PATH robustness: the previous revision invoked the driver with a bare
``quex`` lookup inside a nested ``python test_quex.py -> subprocess quex``
chain. In CI build #96102 that chain failed with
``FileNotFoundError: 'quex'`` (0/4) because the conanrun PATH prepend did
not reach the grandchild process. This revision resolves
``bin/quex`` (and ``share/quex``) absolutely from the dependency
package_folder and passes them as argv, so the driver never depends on
PATH propagation. A python+quex-exe.py fallback covers a broken shebang.
"""

import json
import os
import sys

from conan import ConanFile
from conan.errors import ConanException

EXPECTED_CHECKS = 4


class QuexTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _quex_paths(self):
        pkg_folder = None
        try:
            pkg_folder = self.dependencies["quex"].package_folder
        except Exception:
            pkg_folder = None
        if not pkg_folder:
            try:
                ref = str(self.tested_reference_str).split("@")[0]
                name = ref.split("/")[0]
                pkg_folder = self.dependencies[name].package_folder
            except Exception:
                pkg_folder = None
        if not pkg_folder:
            raise ConanException("quex dependency package_folder unavailable")
        exe = os.path.join(pkg_folder, "bin", "quex")
        share = os.path.join(pkg_folder, "share", "quex")
        main = os.path.join(share, "quex-exe.py")
        return pkg_folder, exe, share, main

    def test(self):
        test_script = os.path.join(os.path.dirname(__file__), "test_quex.py")
        tiny_qx = os.path.join(os.path.dirname(__file__), "tiny.qx")
        if not os.path.isfile(test_script):
            raise ConanException("test_quex.py missing: %s" % test_script)
        if not os.path.isfile(tiny_qx):
            raise ConanException("tiny.qx missing: %s" % tiny_qx)
        pkg_folder, quex_exe, quex_share, quex_main = self._quex_paths()
        self.output.info("quex pkg: %s" % pkg_folder)
        self.output.info("quex exe candidate: %s exists=%s" % (quex_exe, os.path.isfile(quex_exe)))
        self.output.info("quex share: %s exists=%s main=%s" % (
            quex_share, os.path.isdir(quex_share), os.path.isfile(quex_main)))
        if os.path.isfile(quex_exe):
            driver_exe = quex_exe
        elif os.path.isfile(quex_main):
            driver_exe = quex_main
        else:
            try:
                listing = os.listdir(os.path.join(pkg_folder, "bin"))
            except OSError as exc:
                listing = ["<bin list failed: %s>" % exc]
            raise ConanException(
                "neither bin/quex nor share/quex/quex-exe.py found in %s (bin=%s)"
                % (pkg_folder, listing)
            )
        try:
            os.environ["QUEX_PATH"] = quex_share
        except OSError:
            pass
        py = sys.executable or "python3"
        workdir = (
            getattr(self, "test_build_folder", None)
            or getattr(self, "build_folder", None)
            or os.getcwd()
        )
        try:
            os.makedirs(workdir, exist_ok=True)
        except OSError:
            pass
        log_file = os.path.join(workdir, "quex_test_output.log")
        cmd = '"%s" "%s" "%s" "%s" "%s"' % (py, test_script, tiny_qx, driver_exe, quex_share)
        shell_cmd = '%s > "%s" 2>&1' % (cmd, log_file)
        rc = 0
        try:
            self.run(shell_cmd, env="conanrun")
        except Exception as exc:
            rc = 1
            self.output.warning("test driver failed (rc!=0): %s" % exc)
        output = ""
        try:
            with open(log_file, "r", encoding="utf-8", errors="replace") as handle:
                output = handle.read()
        except OSError as exc:
            raise ConanException("test log not found: %s (%s)" % (log_file, exc))
        self.output.info(output[-3000:])
        ok_count = output.count("CHECK-OK:")
        passed = (rc == 0 and ok_count == EXPECTED_CHECKS)
        marker = {
            "executed": True,
            "passed": passed,
            "command": "python3 test_quex.py tiny.qx",
            "discovered": EXPECTED_CHECKS,
            "passedCount": ok_count,
        }
        line = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        print(line, flush=True)
        self.output.info(line)
        if not passed:
            raise ConanException(
                "consumer test failed: rc=%s ok=%s/%s" % (rc, ok_count, EXPECTED_CHECKS)
            )
        self.output.info("quex consumer test_package passed")
