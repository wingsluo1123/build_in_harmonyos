#!/usr/bin/env python3
"""Conan test_package for sqruff 0.39.0 — consumer smoke tests + HMBS re-emit.

1) test.sh runs the 6 consumer cases with the PACKAGED sqruff binary
   (--version / --help / clean lint / dirty lint LT01+LT12 / fix roundtrip /
   ``sqruff lsp`` initialize handshake) and prints HMBS_TEST_PACKAGE_RESULT.
2) The complete upstream cargo suite runs in the main recipe's build() (R51):
   counts are parsed from the real "test result:" lines with hard gates and
   persisted into the package as res/upstream_test_result.json
   (tracexec/0.17.0 范式). hmbs collects HMBS_UPSTREAM_TEST_RESULT from the
   test_package phase stdout only (tlsx/1.2.2 precedent), so this test_package
   re-emits that marker from the packaged record and hard-checks the counts.
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException

# 与主配方 build() 内的硬门禁一致（159 libtest passed；4 upstream ignored）。
_EXPECTED_PASSED = 159


class SqruffTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # ── 1. consumer smoke tests ──
        # test.sh emits HMBS_TEST_PACKAGE_RESULT with real case counts.
        # L0d 门禁静态检查要求 test() 通过 self.run() 实际执行测试程序
        # （无 self.run 调用即判 stub_test_method）；CONFIG_SHELL（HMBS 注入
        # /bin/sh）包住 test.sh；env="conanrun" 让 PATH 含安装后的 bin/。
        sh = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or "sh"
        self.run(
            '%s "%s"' % (sh, os.path.join(self.source_folder, "test.sh")),
            cwd=self.build_folder,
            env="conanrun",
        )

        # ── 2. upstream result re-emit + hard count check ──
        package_folder = self.dependencies["sqruff"].package_folder
        record_path = os.path.join(package_folder, "res",
                                   "upstream_test_result.json")
        if not os.path.isfile(record_path):
            raise ConanException(
                "packaged upstream_test_result.json is missing: %s" % record_path)
        with open(record_path, "r", encoding="utf-8") as handle:
            record = json.load(handle)
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(record, ensure_ascii=False))
        if record.get("status") != "passed" or record.get("failed") != 0:
            raise ConanException(
                "upstream test record is not passing: %s" % record)
        if record.get("passed") != _EXPECTED_PASSED:
            raise ConanException(
                "upstream passed count mismatch: %s != %s"
                % (record.get("passed"), _EXPECTED_PASSED))
