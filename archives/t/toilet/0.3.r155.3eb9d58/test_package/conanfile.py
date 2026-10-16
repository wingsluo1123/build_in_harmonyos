#!/usr/bin/env python3
"""Conan test_package — toilet 消费者端到端验证（HarmonyOS PC 目标机实机执行）。

R34 / 规则 12：本测试**真实执行被测包安装后的 toilet 二进制**完成渲染与导出流程，
并逐字节核对实际业务输出（见 test_e2e.sh 的 HM-E2E-01/02/03）。

刻意不做 `can_run()` 静默跳过：本平台（OHOS/aarch64）构建设备即目标机、build 与 host
profile 相同，消费者用例必须真实执行；若在无法运行二进制的环境下构建，
宁可让测试失败暴露问题，也不静默放过（否则 PR 统计里的「鸿蒙特有测试」就成了空头支票）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class ToiletTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["toilet"]
        pkg_folder = dep.package_folder
        binary = os.path.join(pkg_folder, "bin", "toilet")
        fontdir = os.path.join(pkg_folder, "share", "figlet")

        if not os.path.isfile(binary):
            raise ConanException(
                f"被测包内未找到 toilet 可执行文件：{binary}（包目录 {pkg_folder}）")
        if not os.path.isdir(fontdir):
            raise ConanException(
                f"被测包内未找到字体目录：{fontdir}（期望 share/figlet）")

        # 被测对象来源证据：绝对路径全部落在被测包目录内，供 test_e2e.sh 复核并打印。
        os.environ["TOILET_BIN"] = binary
        os.environ["TOILET_PKG"] = pkg_folder
        os.environ["TOILET_FONTDIR"] = fontdir
        self.output.info(f"消费者被测包目录: {pkg_folder}")
        self.output.info(f"消费者被测二进制: {binary}")
        self.output.info(f"消费者字体目录  : {fontdir}")

        # OHOS 的 /system/bin/sh(mksh) 不能执行 ELF，统一用 profile 指定的 hnp bash 驱动脚本
        # （同 templates/test_package-executable 与 abcm2ps 等先例）。
        shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{shell} test_e2e.sh", env="conanrun")
