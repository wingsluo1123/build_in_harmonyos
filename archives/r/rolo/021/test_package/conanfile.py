#!/usr/bin/env python3
"""Conan test_package — rolo 021 consumer smoke test.

rolo ships one executable (bin/rolo) and no linkable library, so the
consumer cases execute the packaged binary itself (R34):

  (A) rolo resolvable on PATH
  (B) rolo -v prints exactly "rolo 021" with rc 0
  (C) rolo -V prints the GPL blurb with rc 0
  (D) rolo -h prints usage with rc 0
  (E) headless functional run (printf 'qq' | TERM=dumb rolo -f <vCard>)
      quits with rc 0 and leaves the contacts file byte-identical

test.sh maintains deterministic counters (ROLO_TEST_TOTAL/PASS/FAIL);
this file parses them from the real run output to emit
HMBS_TEST_PACKAGE_RESULT — numbers come only from the log, with no
arithmetic patch-ups or fallback guesses.  The upstream marker is staged
at build time (share/doc/rolo/upstream-check.json, parsed from the saved
make check log) and re-emitted byte-verbatim by test.sh.
"""
import json
import os
import re
import shutil

from conan import ConanFile


class RoloTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["rolo"].package_folder
        # Terminfo via staged build-time path (differs from the two prior
        # live-resolution rounds: direct lookup -> None, all-dep scan ->
        # empty; transitive ncurses is not visible in this test context).
        # build() writes the absolute share/terminfo dir (same-cache paths
        # are stable between create's build and test phases) to
        # share/doc/rolo/terminfo-path.txt; read it here and verify isdir.
        # Inline export runs AFTER conanrun.sh sourcing so no aggregation
        # can drop it.  Missing file/dir only warns; suite fails honestly.
        _term = ""
        try:
            _staged = os.path.join(pkg, "share", "doc", "rolo",
                                   "terminfo-path.txt")
            if os.path.isfile(_staged):
                with open(_staged, encoding="utf-8", errors="replace") as _h:
                    _term = _h.read().strip()
                if _term and os.path.isdir(_term):
                    self.output.info(
                        "rolo test_package terminfo: %s (staged)" % _term)
                else:
                    self.output.warning(
                        "rolo test_package staged terminfo unusable: %r"
                        % (_term,))
                    _term = ""
            else:
                self.output.warning(
                    "rolo test_package staged terminfo file missing: %s"
                    % (_staged,))
        except Exception as _exc:
            self.output.warning("rolo test_package staged terminfo read failed: %r"
                                % (_exc,))
            _term = ""
        # Writable tmp root: prefer outer HMBS values when writable, else
        # a build-folder dir (never /tmp directly).
        _tmp_use = ""
        try:
            for _ck in (os.environ.get("TMPDIR") or "",
                        os.environ.get("TMP") or "",
                        os.environ.get("TEMP") or ""):
                if _ck and os.path.isdir(_ck):
                    try:
                        _probe = os.path.join(_ck, ".rolo-tp-wr-probe")
                        with open(_probe, "w", encoding="utf-8") as _h:
                            _h.write("ok\n")
                        try:
                            os.remove(_probe)
                        except OSError:
                            pass
                        _tmp_use = _ck
                        break
                    except OSError:
                        continue
            if not _tmp_use:
                _tmp_use = os.path.join(self.build_folder, "rolo-tp-tmp")
                os.makedirs(_tmp_use, exist_ok=True)
        except Exception as _exc:
            self.output.warning("rolo test_package tmpdir probe failed: %r" % (_exc,))
            _tmp_use = ""
        self.output.info("rolo test_package tmpdir: %s terminfo: %s"
                         % (_tmp_use or "<unset>", _term or "<unset>"))
        _prefix = ""
        if _tmp_use:
            _prefix += ('export TMPDIR="%s"; export TMP="%s"; export TEMP="%s"; '
                        % (_tmp_use, _tmp_use, _tmp_use))
        if _term:
            _prefix += ('export TERMINFO="%s"; export TERMINFO_DIRS="%s"; '
                        % (_term, _term))
        test_sh = os.path.join(self.recipe_folder, "test.sh")
        log = os.path.join(self.build_folder, "rolo_test.log")
        # Never trust a hardcoded HNP bash or a poisoned profile
        # CONFIG_SHELL (both proved inaccessible on some preflight
        # runners: Permission denied on /data/service/hnp).  HMBS
        # guarantees SHELL=/bin/sh; prefer it, then PATH bash, then
        # /bin/sh.  test.sh is POSIX (/bin/sh clean, no pipefail).
        shell = os.environ.get("SHELL") or shutil.which("bash") \
            or shutil.which("sh") or "/bin/sh"
        cmd = '%s\"%s\" \"%s\" \"%s\"' % (_prefix, shell, test_sh, pkg)
        self.run('%s > \"%s\" 2>&1' % (cmd, log), env="conanrun")
        out = ""
        if os.path.isfile(log):
            with open(log, encoding="utf-8", errors="replace") as handle:
                out = handle.read()
        self.output.info("=== rolo test_package (tail) ===")
        for line in (out.splitlines() or [])[-25:]:
            self.output.info(line)

        def _counter(name):
            match = re.search(r"^%s=(\d+)" % name, out, flags=re.MULTILINE)
            return int(match.group(1)) if match else -1

        total = _counter("ROLO_TEST_TOTAL")
        passed = _counter("ROLO_TEST_PASS")
        failed = _counter("ROLO_TEST_FAIL")
        self.output.info("parsed counts: total=%d passed=%d failed=%d"
                         % (total, passed, failed))
        all_ok = (total == 5 and passed == 5 and failed == 0)
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": all_ok,
            "command": "bash test.sh",
            "discovered": total,
            "passedCount": passed,
        }, ensure_ascii=False))
        if not all_ok:
            raise RuntimeError(
                "rolo consumer test failed: total=%d passed=%d failed=%d "
                "(from %s)" % (total, passed, failed, log))
