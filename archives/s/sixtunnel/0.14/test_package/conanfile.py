#!/usr/bin/env python3
"""Conan test_package — sixtunnel (6tunnel) 0.14.

sixtunnel is a single-binary application (bin/6tunnel) built by autotools.
The consumer-level (L1) verification runs the packaged `6tunnel -V`
binary on-device via test.sh: it must execute and print its version string
("6tunnel 0.14").

The upstream functional suite (24 python_def scenarios over IPv4/IPv6
bind/connect + IRC password options) is run inside the main conanfile.py
build() via `make check`, which emits HMBS_UPSTREAM_TEST_RESULT and persists
the result to the package under res/upstream_test_result.json.  This
test_package re-emits HMBS_UPSTREAM_TEST_RESULT from that shipped file on
every round — even when conan reuses a cached binary and skips build()
(cache-proof persistence, autotools-dev/audtty precedent).  If the file is
missing or its status != passed, we raise a ConanException so the gate sees
an honest failure instead of a silent skip.

HMBS_TEST_PACKAGE_RESULT is emitted as a single standalone JSON line after
the real `6tunnel -V` execution, with discovered/passedCount = 1 (the single
real consumer smoke test case in test.sh, sourced directly, not derived by
string-counting).  If test.sh fails, self.run() raises and the marker is
never printed, so a real regression surfaces as a conan failure.
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException


class SixtunnelTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _read_upstream_result(self):
        """Locate the shipped upstream_test_result.json in the dependency pkg."""
        dep_name = "sixtunnel"
        pkg_folder = None
        try:
            pkg_folder = self.dependencies[dep_name].package_folder
        except Exception:
            for dep in self.dependencies.values():
                try:
                    if dep.ref.name == dep_name:
                        pkg_folder = dep.package_folder
                        break
                except Exception:
                    continue
        if not pkg_folder:
            raise ConanException(
                "could not locate sixtunnel package folder for upstream result")
        json_path = os.path.join(pkg_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(json_path):
            raise ConanException(
                "upstream_test_result.json not found at %s "
                "(build() may have been skipped or failed to persist)" % json_path)
        with open(json_path, "r", encoding="utf-8") as _f:
            return json.load(_f)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot exec ELF binaries directly;
        # wrap the smoke test with bash (HNP toolchain bash, same as the
        # test_package-executable template).  test.sh runs in the conanrun
        # env, so the installed bin/6tunnel is on PATH.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")

        # ── 复发放上游测试结果（cache-proof，autotools-dev/audtty 先例）──
        data = self._read_upstream_result()
        if data.get("status") != "passed":
            raise ConanException("upstream test status != passed: %s" % data)
        if data.get("discovered", 0) <= 0 or \
                data.get("executed", 0) != data.get("discovered"):
            raise ConanException(
                "upstream test discovered/executed invalid: %s" % data)
        upstream_marker = "HMBS_UPSTREAM_TEST_RESULT=" + \
            json.dumps(data, ensure_ascii=False)
        self.output.info(upstream_marker)
        print(upstream_marker)

        # ── HMBS_TEST_PACKAGE_RESULT（单行独立 JSON，经验 1）──
        # 真实 `6tunnel -V` 已在上面通过（否则 self.run 已抛异常）。
        # discovered/passedCount == 1：test.sh 中唯一真实消费者用例。
        pkg_result = {
            "executed": True,
            "passed": True,
            "command": "6tunnel -V",
            "discovered": 1,
            "passedCount": 1,
        }
        pkg_marker = "HMBS_TEST_PACKAGE_RESULT=" + \
            json.dumps(pkg_result, ensure_ascii=False)
        self.output.info(pkg_marker)
        print(pkg_marker)
