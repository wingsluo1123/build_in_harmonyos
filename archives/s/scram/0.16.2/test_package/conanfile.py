#!/usr/bin/env python3
"""scram 0.16.2 test_package — CLI 端到端消费者验证。

scram 为概率风险分析命令行工具（SCRAM - Command-line Risk Analysis Multi-tool）。
消费者验证：调用已安装的 scram 二进制执行 --version 与端到端故障树分析，
校验退出码与输出内容。
"""
import os
from conan import ConanFile


class ScramTestConan(ConanFile):
    """test_package for scram — 通过依赖路径定位二进制并运行 test.sh。"""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 从依赖集中定位 scram 包的 bin 目录（key 为完整引用）
        scram_pkg = None
        for ref, dep in self.dependencies.items():
            if dep.ref.name == "scram":
                scram_pkg = dep.package_folder
                break
        if scram_pkg is None:
            raise RuntimeError("依赖集中未找到 scram 包")
        scram_bin = os.path.join(scram_pkg, "bin", "scram")
        if not os.path.exists(scram_bin):
            raise RuntimeError(f"scram 二进制不存在: {scram_bin}")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh {scram_bin}", env="conanrun")
