#!/usr/bin/env python3
"""Conan test_package — wpmeta 0.2.0 (consumer smoke test + upstream evidence).

test() runs two things:

1. ``test.sh`` — 10 real consumer assertion points against the packaged
   ``wpmeta`` binary (5 upstream CLI semantics cases — the end-to-end run plus
   its output-assertion block counted separately — and 3 HarmonyOS-specific
   cases, the preview generation run plus its JPEG artifact block counted
   separately) and prints ``HMBS_TEST_PACKAGE_RESULT``.
2. Upstream test evidence — ``build()`` runs the complete upstream Rust suite
   (10 #[test] cases across the workspace members) on the pristine source and
   persists the parsed counts into ``res/upstream_test_result.json``; this
   stage re-emits ``HMBS_UPSTREAM_TEST_RESULT`` from that record
   (ali/0.8.0 precedent: with a cached binary ``build()`` is skipped, so the
   evidence has to be re-published from the package). The counts are the real
   framework ``test result:`` lines, never placeholders.
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException


class WpmetaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _package_folder(self):
        try:
            return self.dependencies[self.tested_reference_str].package_folder
        except Exception as exc:  # noqa: BLE001 - report, never hide
            raise ConanException(
                f"cannot resolve tested package folder: {exc}")

    def test(self):
        # ── 1. consumer + HarmonyOS-specific cases (test.sh) ──
        shell = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or "sh"
        self.run(f"{shell} test.sh", env="conanrun")

        # ── 2. upstream suite evidence recorded during build() ──
        record_path = os.path.join(self._package_folder(), "res",
                                   "upstream_test_result.json")
        if not os.path.isfile(record_path):
            raise ConanException(
                f"upstream test record missing from the package: {record_path}")
        with open(record_path, encoding="utf-8") as handle:
            record = json.load(handle)
        print("upstream suite recorded during build():", flush=True)
        print(json.dumps(record, ensure_ascii=False, indent=2), flush=True)
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(record), flush=True)
        if record.get("status") != "passed" or record.get("failed", 1) != 0:
            raise ConanException(
                "upstream test record is not a pass: %s" % json.dumps(record))
