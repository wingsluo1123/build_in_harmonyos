#!/usr/bin/env python3
"""Conan test_package — trader 7.21 CLI 二进制验证。

trader 是独立的终端游戏可执行文件（非库），test() 真实执行安装产物
bin/trader：
  - test.c 编译后运行，对二进制做 4 项确定性断言（可执行、--version 版本、
    --help 用法、--no-color --version）；任何一项失败 test.c 返回非零，
    导致 conan create 的 test_package 阶段失败。
  - test.c 结束打印一行确定性尾部标记 `TRADER_TEST_RESULT total=N passed=M
    failed=K`，conanfile 从该标记解析用例计数（单一数据源，不做字符串数数
    或算术修补），据此输出 HMBS_TEST_PACKAGE_RESULT 硬门禁标记。
  - 每轮必跑的 test() 同时复发 HMBS_UPSTREAM_TEST_RESULT(status=no_tests)
    上游测试标记：主配方 build() 不含上游测试命令，且包缓存命中时 build()
    不会重跑，因此由 test_package test() 携带，保证 evidence 门禁每轮都能
    拿到上游测试标记（与 asterisk-flite test_package 同模式）。
  - 两个标记均用裸 print 直接写 stdout，避免 conan 日志前缀导致采集遗漏。
"""
import json
import os
import re
import shlex

from conan import ConanFile
from conan.tools.build import can_run


class TraderTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # test.c 纯 C99 + POSIX，无需额外头文件/链接；直接用 profile 编译器
        # 编译（R33：编译器取自 conan conf，不裸用 shell ${CC}）。
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = (compilers or {}).get("c", "clang")
        self.run(f'"{cc}" -O2 {os.path.join(self.source_folder, "test.c")} '
                 f'-o {os.path.join(self.build_folder, "test_trader")}')

    def test(self):
        if not can_run(self):
            self.output.warning("无法运行测试（交叉编译环境）")
            return
        dep = self.dependencies["trader"]
        bin_path = os.path.join(dep.package_folder, "bin", "trader")
        if not os.path.isfile(bin_path):
            raise Exception(f"trader binary missing: {bin_path}")
        test_bin = os.path.join(self.build_folder, "test_trader")
        out_file = os.path.join(self.build_folder, "test_trader.out")
        # 输出重定向到文件：Conan self.run 只返回退出码，不返回输出，
        # 因此把 test.c 的 stdout/stderr 落到文件再读取（单一数据源）。
        run_cmd = f'"{test_bin}" "{bin_path}" > {shlex.quote(out_file)} 2>&1'
        self.run(run_cmd, env="conanrun", ignore_errors=True)

        text = ""
        if os.path.isfile(out_file):
            with open(out_file, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        self.output.info("test_trader output:\n" + text)

        m = re.search(r"TRADER_TEST_RESULT total=(\d+) passed=(\d+) failed=(\d+)", text)
        if not m:
            test_pkg = {
                "executed": True,
                "passed": False,
                "command": run_cmd,
                "discovered": 0,
                "passedCount": 0,
            }
            print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False), flush=True)
            raise Exception(
                "test.c 未输出确定性结果标记 TRADER_TEST_RESULT（无法确定用例计数）"
            )

        total = int(m.group(1))
        passed_count = int(m.group(2))
        failed = int(m.group(3))
        # 自检恒等式：passed + failed == total 且 total 为正整数
        if passed_count + failed != total or total <= 0:
            test_pkg = {
                "executed": True,
                "passed": False,
                "command": run_cmd,
                "discovered": total,
                "passedCount": passed_count,
            }
            print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False), flush=True)
            raise Exception(
                f"test.c 计数自相矛盾: total={total} passed={passed_count} failed={failed}"
            )

        test_pkg = {
            "executed": True,
            "passed": failed == 0,
            "command": run_cmd,
            "discovered": total,
            "passedCount": passed_count,
        }
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False), flush=True)

        if failed != 0:
            raise Exception(f"trader 消费者测试失败: {passed_count}/{total} 通过")

        # 上游测试标记：trader 7.21 上游无测试套件（详见 MANIFEST.yml 审计）
        upstream_marker = {
            "status": "no_tests",
            "framework": "autotools",
            "command": "make check (upstream has no check/TESTS target)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "trader 7.21 上游无自动化测试套件：顶层 SUBDIRS 为 lib/src/po/"
                "data/doc/m4，无 tests/ 目录；Makefile.am/lib/Makefile.am 均无 "
                "check_PROGRAMS/TESTS/check-local 目标，make check 为 no-op "
                "（本地 configure+make check 实证，详见 MANIFEST.yml "
                "upstream_test_audit）。"
            ),
        }
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker, ensure_ascii=False), flush=True)
