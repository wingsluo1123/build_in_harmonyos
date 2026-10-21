#!/usr/bin/env python3
"""Conan recipe — w-calc 2.5 (autotools).

w-calc is an arbitrary-precision command-line scientific calculator built on
GMP and MPFR. This recipe builds the native OHOS (aarch64) CLI and runs the
upstream automake test-suite through `make check`.

OHOS notes:
  * The released `configure` creates its `config.status` temporary directory
    with `umask 077 && mktemp -d ./confXXXXXX`. On OHOS HMDFS the resulting
    directory is not writable by the build user, so `config.status` fails with
    `subs1.awk: Permission denied`. Patch 0001 changes those two umasks to 022
    (knowledge entry E011), applied only for os=OHOS. `configure` is a
    generated file, so the fix is delivered as a patch (R6) rather than a
    runtime edit.
  * Readline is an optional dependency; `--without-readline` drops it. Plain
    standard input keeps working, only history/completion are unavailable.
  * GMP/MPFR are supplied by the published `gmp/6.3.0` and `mpfr/4.2.2.1`
    Conan packages and located via `--with-gmp` / `--with-mpfr`.
  * settings.os is compared with `in ("Linux", "OHOS")` (R32); no shell
    variables are read in build() (R33).
"""
import json
import os
import time

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import load_toolchain_args
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout

# wcalc 2.5 registers 21 automake tests in test/Makefile.am: 12 positive
# (POSITIVE_TESTS) and 9 expected-failure (XFAIL_TESTS). The count below is the
# declared upstream total and must match test/test-suite.log # TOTAL.
UPSTREAM_TEST_TOTAL = 21


class WcalcConan(ConanFile):
    name = "w-calc"
    version = "2.5"
    description = "Arbitrary-precision command-line scientific calculator (GMP/MPFR)"
    license = "GPL-2.0-or-later"
    homepage = "https://wcalc.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Published packages; mpfr/4.2.2.1 requires gmp/6.3.0 exactly.
        self.requires("gmp/6.3.0")
        self.requires("mpfr/4.2.2.1")

    def validate(self):
        # R32: OHOS must be matched alongside Linux.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "w-calc only supports Linux/OHOS, got %s" % self.settings.os
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # HMDFS fork pressure: every self.run wraps the command as
        # `. conanbuild.sh && <cmd>`. The generated env scripts begin with a
        # deactivation preamble that forks `printenv` once per variable. On a
        # loaded HarmonyOS worker that burst of short-lived processes trips the
        # process-table limit and the very next fork dies with
        # `can't fork - try again` — CI #91942 died at line 13 of
        # conanautotoolstoolchain.sh (exactly the `$(printenv $v)` in the
        # preamble), and #92079/#93107 died at the following fork inside
        # `make`. `deactivation_mode=function` rewrites the preamble to only
        # *define* a deactivation function using pure shell builtins (no fork
        # at source time) while exporting the same variables, so the burst is
        # removed at its source rather than retried after it fails.
        self.conf.define("tools.env:deactivation_mode", "function")
        gmp = self.dependencies["gmp"]
        mpfr = self.dependencies["mpfr"]
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--without-readline",
            "--with-gmp=%s" % gmp.package_folder,
            "--with-mpfr=%s" % mpfr.package_folder,
        ])
        tc.generate()
        # Inject GMP/MPFR include+lib dirs into the conanbuild environment so
        # the compiler probes and the final link find the dependencies.
        AutotoolsDeps(self).generate()

    def build(self):
        # [shell_getcwd] The shared OHOS profile [buildenv] exports
        # CONFIG_SHELL=/data/service/hnp/bin/bash (and SHELL likewise). autoconf
        # `configure` unconditionally `exec "$CONFIG_SHELL"` when it is
        # non-empty, and that hnp bash cannot getcwd() on the HMDFS build tree:
        # it emits a `shell-init: error retrieving current directory` storm and
        # then dies with `configure: error: working directory cannot be
        # determined`. Append an override at the end of the sourced
        # conanbuild.sh so configure/make run under /bin/sh (toybox sh), whose
        # getcwd works. parted/3.8 and tetradraw/2.0.3 use the same fix.
        if self.settings.os == "OHOS":
            self._neutralize_config_shell()
            # PWD lets the shell's `pwd` take the logical path instead of the
            # failing getcwd() (adms/2.3.7, air-quality-sensor/0.1.5).
            os.environ["PWD"] = self.build_folder
            apply_conandata_patches(self)
        self._configure_with_fork_retry()
        # E011: configure regenerates config.status from the same template, so
        # its temp-dir block again uses `umask 077`. If make check re-runs
        # config.status on HMDFS the same Permission-denied failure returns;
        # neutralise it at runtime for OHOS only (generated file, not a patch).
        if self.settings.os == "OHOS":
            self._fix_config_status_umask()
        # E074: parallel make trips the HMDFS jobserver fifo; stay serial.
        # Fork-gated retry: make forks sh/compiler children and can hit the
        # same transient EAGAIN as configure (#92079: `/bin/sh: can't fork -
        # try again` while `Making all in common`).
        self._make_with_fork_retry()
        # ── Upstream official test-suite (make check) ──
        self._run_upstream_checks()

    def _run_with_fork_retry(self, label, cmd, log_path, cwd=None,
                             diag_paths=()):
        """Run `cmd`, retrying a bounded number of times on fork EAGAIN.

        Both `configure` and `make` fork hundreds of sh/compiler/sub-make
        children; the conanbuild.sh they source also spawns `printenv`
        subshells per variable. On a loaded shared worker the device
        intermittently refuses to fork and the step aborts before finishing —
        the CI logs show `configure` dying at
        `conanautotoolstoolchain.sh[13]: can't fork - try again` (#91942) and
        later `make` dying at `/bin/sh: can't fork - try again` inside
        `Making all in common` (#92079), alongside an unrelated
        `knowledge_check.sh: fork: retry: Resource temporarily unavailable` on
        the same machine. That is transient process-table exhaustion, not a
        recipe defect, so retry only when the captured output actually shows
        fork pressure; any other failure is re-raised on the first attempt so
        genuine build errors are never masked.
        Same bounded fork-retry already merged for synscan/5.02 and libcmis.

        The same recipe revision passed on one worker (#93377) and failed on
        two others (#93618, #93656) at the very same `Making all in common`
        fork, so the pressure window can outlast a 45s retry. The backoff is
        therefore exponential (15/30/60/120s) with more attempts, and the
        zero-fork `deactivation_mode=function` preamble (see generate()) has
        already removed the per-variable `printenv` burst that used to seed it.

        ``diag_paths`` lists files the tool writes its *real* diagnostics into
        instead of its own stdout/stderr. autoconf `configure` is the prime
        case: when the compiler probe fails it prints only the generic
        `C compiler cannot create executables` on stdout and writes the actual
        compiler/linker error (e.g. a fork EAGAIN inside the probe, or an
        lld/libxml2 load failure) to ``config.log``. Without reading that file
        the fork gate never sees the fork markers and the retry never fires —
        CI #93820 died at `attempt 1/5, rc=77` exactly this way. These files
        are removed before each attempt and their content is both printed for
        diagnosis and folded into the fork-marker scan.
        """
        fork_markers = ("can't fork", "cannot fork", "try again",
                        "resource temporarily unavailable")
        attempts = 5
        for attempt in range(1, attempts + 1):
            # Drop stale diagnostics so a previous attempt cannot seed the
            # fork-marker scan for this one.
            for dpath in diag_paths:
                try:
                    os.remove(dpath)
                except OSError:
                    pass
            ret = None
            fork_exc = None
            try:
                with open(log_path, "w", encoding="utf-8") as handle:
                    ret = self.run(cmd, ignore_errors=True, cwd=cwd,
                                   stdout=handle, stderr=handle)
            except Exception as exc:  # conan_run raises on Popen fork failure
                fork_exc = exc
            detail = ""
            try:
                with open(log_path, encoding="utf-8", errors="replace") as handle:
                    detail = handle.read()
            except OSError:
                pass
            # Keep the captured output visible in the CI log.
            if detail:
                print(detail, flush=True)
            # Surface the tool's own diagnostic log (autoconf config.log),
            # where the real compiler/linker error is written. Only on a
            # failed attempt, to keep the successful CI log readable.
            diag = ""
            if ret != 0:
                for dpath in diag_paths:
                    try:
                        with open(dpath, encoding="utf-8", errors="replace") as handle:
                            diag += "\n===== %s =====\n%s" % (dpath, handle.read())
                    except OSError:
                        pass
                if diag:
                    print(diag, flush=True)
            if ret == 0:
                return
            combined = ("%s\n%s\n%s" % (fork_exc or "", detail, diag)).lower()
            hit_fork_pressure = any(m in combined for m in fork_markers)
            if attempt >= attempts or not hit_fork_pressure:
                raise ConanException(
                    "w-calc %s failed (attempt %d/%d, rc=%s): %s"
                    % (label, attempt, attempts, ret,
                       (detail + diag or str(fork_exc))[-4000:]))
            wait = 15 * (2 ** (attempt - 1))  # 15s, 30s, 60s, 120s
            self.output.warning(
                "w-calc %s hit fork pressure (attempt %d/%d, rc=%s); "
                "sleeping %ds then retrying" % (label, attempt, attempts, ret, wait))
            time.sleep(wait)

    def _configure_with_fork_retry(self):
        """Run `configure` under the fork-gated retry.

        autoconf writes the real compiler/linker diagnostic to ``config.log``
        in the build folder (the configure stdout only carries the generic
        `C compiler cannot create executables`), so that file is passed as a
        diagnostic source for both the CI log and the fork-marker scan.
        """
        configure_args = load_toolchain_args(self.generators_folder).get(
            "configure_args", "")
        cmd = '"%s/configure" %s' % (self.source_folder, configure_args)
        log_path = os.path.join(self.build_folder, "configure.log")
        diag = []
        for root in (self.build_folder, self.source_folder):
            if root:
                path = os.path.join(root, "config.log")
                if path not in diag:
                    diag.append(path)
        self._run_with_fork_retry(
            "configure", cmd, log_path, diag_paths=tuple(diag))

    def _make_with_fork_retry(self, target=None, log_name="make.log"):
        """Run `make` under the fork-gated retry.

        The make program and make_args are resolved the same way Conan's
        Autotools helper does (``tools.gnu:make_program``, defaulting to
        ``make``; ``make_args`` from the generated conanbuild.conf), so only
        ``-j1`` (E074) is appended here.
        """
        make_program = self.conf.get("tools.gnu:make_program", default="make")
        make_args = load_toolchain_args(self.generators_folder).get(
            "make_args", "")
        cmd = " ".join(filter(None, [make_program, target, make_args, "-j1"]))
        log_path = os.path.join(self.build_folder, log_name)
        self._run_with_fork_retry("make", cmd, log_path)

    def _install_with_fork_retry(self):
        """Run `make install` under the fork-gated retry with `-j1`.

        `Autotools(self).install()` appends no `-j`, so GNU make picks
        ``build_jobs`` (the host core count) — the passing CI log shows
        ``make install ... -j20``. That parallel install fork-bursts the same
        sh/install children as the build and is the one remaining step not yet
        covered by the fork-gated retry, so route it through the same
        ``-j1`` + bounded-retry path. The package folder is passed as DESTDIR
        exactly like the Autotools helper does.
        """
        make_program = self.conf.get("tools.gnu:make_program", default="make")
        make_args = load_toolchain_args(self.generators_folder).get(
            "make_args", "")
        cmd = " ".join(filter(None, [make_program, "install",
                                     "DESTDIR=%s" % self.package_folder,
                                     make_args, "-j1"]))
        log_path = os.path.join(self.build_folder, "make-install.log")
        self._run_with_fork_retry("make install", cmd, log_path)

    def _neutralize_config_shell(self):
        """Override the profile's CONFIG_SHELL/SHELL to /bin/sh for OHOS.

        The shared ohos-aarch64 profile [buildenv] sets
        CONFIG_SHELL=/data/service/hnp/bin/bash and SHELL likewise. autoconf
        `configure` re-execs into $CONFIG_SHELL when it is non-empty, and that
        hnp bash cannot getcwd() on the HMDFS build tree (shell-init/job-
        working-directory errno storm ending in `configure: error: working
        directory cannot be determined`). Generator aggregation places the
        profile buildenv at the end of conanbuild.sh, so we append our override
        last; /bin/sh is toybox sh, whose getcwd works. Same fix as parted/3.8
        and tetradraw/2.0.3.
        """
        script = os.path.join(self.generators_folder, "conanbuild.sh")
        if os.path.isfile(script):
            with open(script, "a", encoding="utf-8") as fh:
                fh.write("\nexport CONFIG_SHELL=/bin/sh\nexport SHELL=/bin/sh\n")
            self.output.info(
                "buildenv: CONFIG_SHELL/SHELL overridden to /bin/sh "
                "(HMDFS getcwd fix)"
            )

    def _fix_config_status_umask(self):
        for root in (self.build_folder, self.source_folder):
            if not root:
                continue
            path = os.path.join(root, "config.status")
            if not os.path.isfile(path):
                continue
            try:
                with open(path, "r", encoding="utf-8",
                          errors="surrogateescape") as fh:
                    content = fh.read()
            except OSError:
                continue
            if "umask 077" not in content:
                continue
            with open(path, "w", encoding="utf-8",
                      errors="surrogateescape") as fh:
                fh.write(content.replace("umask 077", "umask 022"))
            self.output.info("config.status umask 077->022 patched: %s" % path)

    def _run_upstream_checks(self):
        """Run the upstream automake suite and emit HMBS_UPSTREAM_TEST_RESULT.

        All 21 registered tests are executed; numbers come from the automake
        parallel-tests summary block in test/test-suite.log. XFAIL is counted
        as passed because it is the outcome upstream explicitly declares for
        those cases (XFAIL_TESTS in test/Makefile.am), i.e. the test behaved as
        expected rather than being skipped.
        """
        check_rc = 0
        check_error = ""
        try:
            # Fork-gated retry around `make check` too: the suite re-runs the
            # wcalc binary and checktest.sh shells, so a transient process-table
            # spike here would otherwise look like a test failure.
            self._make_with_fork_retry(target="check", log_name="make-check.log")
        except Exception as exc:  # still emit the real counts, then fail
            check_rc = 1
            check_error = repr(exc)

        result = self._upstream_result(check_rc, check_error)
        line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False)
        print(line, flush=True)
        self.output.info(line)

        if result["status"] != "passed":
            self._dump_suite_log()
            raise ConanException(
                "w-calc upstream make check did not pass: "
                + result.get("reason", json.dumps(result, ensure_ascii=False))
            )

    def _find_suite_log(self):
        for root in (self.build_folder, self.source_folder):
            if not root or not os.path.isdir(root):
                continue
            direct = os.path.join(root, "test", "test-suite.log")
            if os.path.isfile(direct):
                return direct
            for dirpath, _dirnames, filenames in os.walk(root):
                if "test-suite.log" in filenames:
                    return os.path.join(dirpath, "test-suite.log")
        return None

    def _upstream_result(self, check_rc, check_error):
        log_path = self._find_suite_log()
        command = "make check"
        if log_path is None:
            reason = (
                "test/test-suite.log not found after make check (rc=%d); "
                "searched test/test-suite.log under build_folder=%s and "
                "source_folder=%s" % (check_rc, self.build_folder, self.source_folder)
            )
            if check_error:
                reason += "; " + check_error
            return {
                "status": "failed",
                "framework": "automake",
                "command": command,
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": reason,
            }

        counts = {}
        with open(log_path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line.startswith("# "):
                    continue
                key, _, value = line[2:].partition(":")
                key = key.strip()
                value = value.strip()
                if key in ("TOTAL", "PASS", "FAIL", "SKIP", "XFAIL", "XPASS", "ERROR"):
                    try:
                        counts[key] = int(value)
                    except ValueError:
                        pass

        total = counts.get("TOTAL", 0)
        # XFAIL is an upstream-declared expected outcome, not a skip.
        passed = counts.get("PASS", 0) + counts.get("XFAIL", 0)
        failed = (
            counts.get("FAIL", 0)
            + counts.get("XPASS", 0)
            + counts.get("ERROR", 0)
        )
        skipped = counts.get("SKIP", 0)
        executed = total - skipped

        marker = {
            "status": "passed" if (check_rc == 0 and failed == 0 and total > 0
                                   and executed == passed) else "failed",
            "framework": "automake",
            "command": command,
            "discovered": total,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        if total != UPSTREAM_TEST_TOTAL:
            marker["status"] = "failed"
            marker["reason"] = (
                "test-suite.log TOTAL=%d does not match the %d tests declared in "
                "test/Makefile.am" % (total, UPSTREAM_TEST_TOTAL)
            )
        elif marker["status"] != "passed":
            marker["reason"] = (
                "make check rc=%d; test-suite.log TOTAL=%d PASS=%d XFAIL=%d "
                "FAIL=%d XPASS=%d ERROR=%d SKIP=%d"
                % (check_rc, total, counts.get("PASS", 0), counts.get("XFAIL", 0),
                   counts.get("FAIL", 0), counts.get("XPASS", 0),
                   counts.get("ERROR", 0), skipped)
                + (("; " + check_error) if check_error else "")
            )

        # Persist evidence in the build folder; package() copies it into the
        # package so test_package can re-emit it on cached rebuilds.
        try:
            save(self, os.path.join(self.build_folder, "upstream_test_result.json"),
                 json.dumps(marker, ensure_ascii=False))
        except Exception:
            pass
        return marker

    def _dump_suite_log(self):
        log_path = self._find_suite_log()
        if not log_path:
            return
        with open(log_path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                self.output.info("TSLOG: " + line.rstrip("\n"))

    def package(self):
        self._install_with_fork_retry()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # Carry the upstream-test evidence into the package so test_package can
        # re-emit the marker on cached rebuilds (build() is skipped then).
        res_dir = os.path.join(self.package_folder, "res")
        os.makedirs(res_dir, exist_ok=True)
        marker_path = os.path.join(res_dir, "upstream_test_result.json")
        if os.path.isfile(os.path.join(self.build_folder,
                                       "upstream_test_result.json")):
            copy(self, "upstream_test_result.json", src=self.build_folder,
                 dst=res_dir)
        elif not os.path.isfile(marker_path):
            save(self, marker_path, json.dumps({
                "status": "failed",
                "framework": "automake",
                "command": "make check",
                "discovered": 0, "executed": 0, "passed": 0,
                "failed": 0, "skipped": 0,
                "reason": "upstream marker missing at package time",
            }, ensure_ascii=False))

    def package_info(self):
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
