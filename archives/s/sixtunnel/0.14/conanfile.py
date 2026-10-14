#!/usr/bin/env python3
"""Conan recipe — sixtunnel (6tunnel) 0.14.

6tunnel is a TCP proxy/tunnel that lets an IPv4-only client reach IPv6
services and vice-versa. It is a single C file (6tunnel.c) built by a
minimal autotools project producing a single `bin/6tunnel` executable.

Upstream tests:
  Makefile.am registers `TESTS = ./test.py` (automake harness).  test.py
  contains 24 `test(...)` scenario calls (python_def methodology) covering
  the IPv4/IPv6 endpoint combinations, the -4/-6/-l/-s binding options and
  the IRC -I/-i password options.  test.py runs every scenario sequentially
  and aborts on the first failure (raises Exception), so a `make check` exit
  status of 0 guarantees all 24 cases genuinely executed and passed.  This
  was sanity-checked by stubbing `6tunnel` with `exit 1`: test.py then fails
  with "expected success yet command failed" (rc 1), proving the harness
  catches failures (it is not silently passing empty scenarios).

The HMBS_UPSTREAM_TEST_RESULT marker counts are derived from a single
deterministic source (the `test(` invocations in source/test.py for
discovered; the teed `make check` log's "Running with" lines for executed/
passed/failed on the failure path).  On success every scenario passed so
executed == passed == discovered == 24.  The identity passed + failed ==
executed is guaranteed in both branches.
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SixtunnelConan(ConanFile):
    name = "sixtunnel"
    version = "0.14"
    description = ("6tunnel — IPV4/IPv6 TCP proxy/tunnel that lets IPv4-only "
                   "applications reach IPv6 services and vice-versa")
    license = "GPL-2.0-only"
    homepage = "https://toxygen.net/6tunnel/"
    url = "https://github.com/wojtekka/6tunnel"
    topics = ("ipv6", "ipv4", "proxy", "tunnel", "tcp")

    # 纯可执行产物（bin/6tunnel），非库。
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def _patch_configure_for_ohos(self):
        """Make autoconf's temp-dir helper use a writable mkdir fallback.

        The generated ``configure``/``config.status`` create their scratch
        directory via ``tmp=`(umask 077 && mktemp -d "./confXXXXXX")``, with
        the fallback ``tmp=./conf$-$RANDOM; (umask 077 && mkdir "$tmp")``.
        On the HarmonyOS HMDFS build volume the directory that either branch
        creates under ``umask 077`` comes out as ``drwx--S---`` (042700): the
        volume is setgid with a mapped owner uid, so the build process ends
        up with no usable write path and config.status aborts with
        ``./conf*/subs1.awk: Permission denied`` ->
        ``config.status: error: could not setup config files machinery``.

        A PATH-prepended mktemp wrapper cannot fix this here: the platform
        reports ``chmod`` capability 0, so a Python-written shim cannot be
        made executable and mktemp is never shadowed (an earlier round's
        failing temp dir ``confmhiLJm`` was still mktemp-generated).

        Fix (canonical repo pattern, a52dec/qprint/inn2):
        1. Relax ``umask 077`` -> ``umask 022`` in both the mktemp and mkdir
           branches; ``umask 022`` yields ``drwxr-s--x``/``drwxr-xr-x`` which
           the build process CAN write into.
        2. Replace the ``mktemp -d "<template>"`` invocation with ``false`` so
           the mkdir fallback always runs, removing any dependence on the
           platform mktemp honoring the umask (toybox mktemp behaviour is
           inconsistent across builds).  The fallback mkdir deterministically
           honors the umask.

        The AS_TMPDIR block is copied verbatim into the generated
        config.status, so patching ``configure`` before running it also fixes
        config.status (config.status reuses configure's ``$ac_tmp`` and has
        no independent mktemp).  In-place text rewrite keeps the exec bit (no
        chmod needed).  Applied unconditionally; it does not depend on an env
        var the preflight may not export.
        """
        cfg = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(cfg):
            self.output.info("sixtunnel configure not present; skipping patch")
            return
        with open(cfg, encoding="utf-8", errors="surrogateescape") as f:
            s = f.read()
        # (1) Relax the AS_TMPDIR umask in both branches (077 -> 022).
        s = s.replace("(umask 077 && mktemp", "(umask 022 && mktemp")
        s = s.replace("(umask 077 && mkdir", "(umask 022 && mkdir")
        # (2) Force the mkdir fallback by making mktemp always fail.
        marker = "mktemp -d "
        i = s.find(marker)
        if i == -1:
            self.output.info(
                "sixtunnel configure mktemp pattern not found; leaving as-is")
            return
        if s[i + len(marker):i + len(marker) + 1] != '"':
            self.output.info(
                "sixtunnel configure mktemp template not quoted; leaving as-is")
            return
        j = s.find('"', i + len(marker) + 1)
        if j == -1:
            self.output.info(
                "sixtunnel configure mktemp closing quote not found; "
                "leaving as-is")
            return
        s = s[:i] + "false" + s[j + 1:]
        with open(cfg, "w", encoding="utf-8", errors="surrogateescape",
                  newline="") as f:
            f.write(s)
        self.output.info(
            "sixtunnel configure patched: umask 022 + mktemp disabled, "
            "mkdir fallback active")

    def build(self):
        apply_conandata_patches(self)

        # HMFS 平台诊断 [shell_getcwd]：HMDFS 对 conan 构建树父目录不提供
        # getcwd()，autoconf `pwd` 可能失败（adcli/adms/aircrack 同款）。
        # 预置 PWD 让 shell pwd 内建走逻辑路径，避免 configure 报
        # "working directory cannot be determined"。
        os.environ["PWD"] = self.build_folder

        autotools = Autotools(self)
        # HMBS 平台诊断 [unsafe_local_mktemp]：autoconf 的 AS_TMPDIR 用
        # `(umask 077 && mktemp -d "./confXXXXXX")` 建临时目录，回退分支为
        # `tmp=./conf$-$RANDOM; (umask 077 && mkdir "$tmp")`。HMFS 为 setgid
        # 卷且属主 uid 被映射，umask 077 下两分支建出的目录都是 drwx--S---
        # (042700)，构建进程无可用写路径，config.status 写 subs1.awk 报
        # "./conf*/subs1.awk: Permission denied / could not setup config files
        # machinery"（上一轮 mktemp→false 后回退目录名变为 conf$-$RANDOM 的
        # conf38156-19156，仍失败，证实根因是 umask 077 而非 mktemp 本身）。
        # 修法（a52dec/qprint/inn2 仓内同形）：① 两处 umask 077→022，建出
        # drwxr-s--x 可写；② 把 mktemp -d 调用替换为 false，强制走 mkdir 回退
        # （mkdir 确定性地遵守 umask，不依赖平台 mktemp 行为）。AS_TMPDIR 块
        # 原样嵌入生成的 config.status，故改 configure 同时修复 config.status。
        self._setup_writable_tmpdir()
        self._patch_configure_for_ohos()
        autotools.configure()
        autotools.make(args=["-j1"])
        # ── 上游官方测试 (make check → test.py) ──
        self._run_upstream_checks()

    def _count_test_cases(self):
        """Count the 24 test(...) scenario invocations in source/test.py.

        Deterministic source-of-truth count (python_def methodology):
        every top-level `test(` call is one real scenario.
        """
        test_py = os.path.join(self.source_folder, "test.py")
        count = 0
        if os.path.isfile(test_py):
            with open(test_py, encoding="utf-8", errors="replace") as f:
                for line in f:
                    if line.lstrip().startswith("test("):
                        count += 1
        return count

    def _setup_writable_tmpdir(self):
        """Export a writable TMPDIR for the configure subprocess.

        HMBS injects a writable runtime tmp dir (HMBS_TMPDIR / TMPDIR);
        prefer it, otherwise fall back to the conan build folder which is
        guaranteed writable by conan.  The value is exported into os.environ
        so configure/config.status and its helper tools create any scratch
        files under a writable location (the autoconf AS_TMPDIR directory
        itself is handled separately by the in-place configure rewrite in
        _patch_configure_for_ohos()).
        """
        candidates = []
        for key in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(key)
            if val:
                candidates.append(val)
        candidates.append(self.build_folder)
        for cand in candidates:
            if cand and os.path.isdir(cand):
                os.environ["TMPDIR"] = cand
                os.environ.setdefault("TMP", cand)
                os.environ.setdefault("TEMP", cand)
                self.output.info("sixtunnel AS_TMPDIR redirect TMPDIR=%s" % cand)
                return
        self.output.info("sixtunnel AS_TMPDIR redirect: no writable tmpdir found")

    def _run_upstream_checks(self):
        """Run upstream `make check` and emit HMBS_UPSTREAM_TEST_RESULT.

        - discovered comes from counting `test(` calls in source/test.py.
        - On `make check` success every scenario passed (test.py aborts on
          first failure), so executed == passed == discovered.
        - On failure we count the teed "Running with" lines (test.py prints
          one per case on entry) to attribute executed/passed/failed while
          keeping the identity passed + failed == executed intact.
        - The result is persisted (upstream_test_result.json) and shipped in
          the package so test_package can re-emit the marker even when conan
          skips build() on a cached binary ("Already installed!").
        """
        discovered = self._count_test_cases()

        log = os.path.join(self.build_folder, "make-check.log")
        rc = 0
        try:
            self.run('set -o pipefail; make check -j1 2>&1 | tee "%s"' % log,
                     cwd=self.build_folder, env="conanbuild")
        except Exception:
            rc = 1
            # 失败时把 automake test-suite.log 的失败详情段输出到构建日志，
            # 便于 CI/真机日志直接定位。
            suite_log = os.path.join(self.build_folder, "test-suite.log")
            if os.path.isfile(suite_log):
                with open(suite_log, encoding="utf-8", errors="replace") as f:
                    for line in f:
                        self.output.info("TSLOG: " + line.rstrip("\n"))

        if rc == 0:
            executed = passed = discovered
            failed = skipped = 0
            status = "passed"
        else:
            # make check 失败 —— test.py 顺序执行并在首个失败处中止。
            running = 0
            if os.path.isfile(log):
                with open(log, encoding="utf-8", errors="replace") as f:
                    for line in f:
                        if "Running with" in line:
                            running += 1
            executed = running
            if executed > 0:
                # 最后一个已进入的用例是失败的，其余已完整通过。
                passed = executed - 1
                failed = 1
            else:
                passed = 0
                failed = 0
            skipped = 0
            status = "failed"

        marker = {
            "status": status,
            "framework": "python_def (via automake make check)",
            "command": "make check",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        if status != "passed":
            marker["reason"] = ("upstream test.py did not pass on the device; "
                                "see test-suite.log / make-check.log")

        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" +
                         json.dumps(marker, ensure_ascii=False))

        # 持久化到构建目录，package() 会把它放进包内 res/，
        # 供 test_package 在缓存命中时复发标记。
        result_path = os.path.join(self.build_folder, "upstream_test_result.json")
        with open(result_path, "w", encoding="utf-8") as _f:
            json.dump(marker, _f, ensure_ascii=False)
        self.output.info("persisted upstream test result to {}".format(result_path))

        if status != "passed":
            raise ConanException(
                "upstream make check failed: " + json.dumps(marker, ensure_ascii=False))

    def package(self):
        autotools = Autotools(self)
        autotools.install()

        # 把上游测试结果随包交付，供 test_package 复发 HMBS_UPSTREAM_TEST_RESULT。
        result_path = os.path.join(self.build_folder, "upstream_test_result.json")
        if os.path.isfile(result_path):
            res_dir = os.path.join(self.package_folder, "res")
            os.makedirs(res_dir, exist_ok=True)
            copy(self, "upstream_test_result.json",
                 self.build_folder, res_dir, keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
