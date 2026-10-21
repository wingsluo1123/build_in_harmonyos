#!/usr/bin/env python3
"""test_package for ply-probe — CLI 追踪前端（application 包）。

测试策略（R34：必须实质依赖被测包；R51：上游测试不可运行时补鸿蒙独有测试）：
  上游 test/ 的 QEMU 套件与 src/ply/self-test.sh 都要求 Linux 内核追踪后端，
  在本平台不可运行（bpf() → SIGSYS，见 reports/probe-output.log）。
  故本测试执行**被测包的真实二进制**：ply -v / ply -h 与脚本解析器（含非法脚本负例）；
  ply -e 仅作 kallsyms 边界断言，不执行 ply -S / ply -T（二者会下沉到 bpf() 被 SIGSYS 终止）。
"""
import os

from conan import ConanFile


class PlyProbeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run("{} test.sh".format(bash), env="conanrun")
