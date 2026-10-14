#!/usr/bin/env python3
"""test_package for xmlto 0.0.29 —— CLI 工具消费者端到端用例（HarmonyOS PC）。

真实测试逻辑在 consumer_test.sh 中执行（非空壳、非 print-only），
入口通过 self.run() 真实运行测试程序并校验退出码：

  A. HarmonyOS 专有非断言测试 —— 原生 ELF 与动态依赖闭包加载
     A1 xmlif 必须是 OHOS aarch64 原生 ELF 可执行文件
     A2 xmlif 的 DT_NEEDED 动态依赖闭包必须存在且含 libc.so
     A3 闭包在本机真实加载：原生执行 xmlif，由动态加载器解析整个闭包

  B. 端到端消费者用例（构造输入 -> 真实执行业务 -> 产出结果 -> 校验内容）
     B1 xmlto 真实转换：XML + 自定义 XSL -> HTML 产物并校验产物内容
     B2 xmlif 条件过滤：复现上游手册用例（xmlif/test/test.xml），
        与上游期望输出逐字节比对

全部判定基于命令退出码（self.run / cmp），不使用 Python assert。
"""
import os

from conan import ConanFile


class XmltoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bindir = self.dependencies["xmlto"].cpp_info.bindirs[0]
        script = os.path.join(self.recipe_folder, "consumer_test.sh")
        self.output.info(f"运行消费者端到端用例: sh {script} {bindir}")
        # 通过解释器调用，避免 HMDFS 上脚本文件的 execve 限制
        self.run(f'sh "{script}" "{bindir}"', env="conanrun")
