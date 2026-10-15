#!/usr/bin/env python3
"""Conan test_package for rna-star 2.7.11b.

rna-star 是命令行工具（非库），因此消费测试直接驱动安装的 ELF 二进制：
`STAR --version`（exit 0，输出 2.7.11b）与 `STAR --help`（usage，输出
"STAR version=2.7.11b"）。两者都真实调用打包产物，回应 R34 非空壳测试。
"""
import json
import os
import shutil

from conan import ConanFile


class RnaStarTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def configure(self):
        # 与主配方同因：conan 默认在 conanrunenv-*.sh 顶部生成 source 时
        # 立即执行的反激活前导块（逐变量 fork printenv + 命令替换子 shell）。
        # 本包 runenv 含 PATH（application 包 bin/），真机 fork 紧张时
        # `. conanrun.sh` 会报 `can't fork - try again`。切为函数形态后
        # source 时不执行、零 fork，仍完整导出 runenv。
        # 必须放 configure()：本包显式声明 generators="VirtualRunEnv"，它在
        # generate() 之前执行；generate() 里改 conf 对显式生成器无效。
        self.conf.define("tools.env:deactivation_mode", "function")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) 不能执行 ELF 二进制；用 hnp bash 包裹。
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") \
            or "/data/service/hnp/bin/bash"
        script = os.path.join(self.source_folder, "test_rna_star.sh")
        self.run(f"{bash} {script}", env="conanrun")

        # HMBS 上游机器证据标记：rna-star 上游无任何测试（见
        # test_package/MANIFEST.yml 的 upstream_test_audit 审计结论——
        # Makefile 无 check/test 目标、CI(.travis) 仅 make STAR、无任何测试
        # 框架声明，upstream_test_total: 0）。在真实运行 test_package 之后再
        # 复发行，status=no_tests、各计数为 0。
        upstream_marker = {
            "status": "no_tests",
            "framework": "none",
            "command": "",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": ("upstream rna-star 2.7.11b 无任何正式测试套件；审计见 "
                       "test_package/MANIFEST.yml 的 upstream_test_audit（Makefile "
                       "仅 all/STAR/STARstatic/STARlong/gdb 等构建目标，无 check/test；"
                       ".travis.yml 仅 make STAR；extras/tests 仅 awk 分析辅助脚本；"
                       "全仓无 ctest/gtest/make check/meson test 声明），"
                       "upstream_test_total: 0"),
        }
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker))
