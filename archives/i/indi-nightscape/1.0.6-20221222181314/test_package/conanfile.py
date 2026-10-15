#!/usr/bin/env python3
"""Conan test_package — indi-nightscape 1.0.6-20221222181314 (Conan L1 official test).

R34 实质测试：执行被测包安装的二进制 (驱动 indi_nightscape_ccd 依赖的 INDI
共享库在 OHOS 上无法加载——E537/R49 教训同款；因此实际运行的是上游测试工具
nstest，验证 libftdi/libusb 依赖链在运行时真实加载，并检查安装产物完整)。
无硬件时 nstest 预期输出 "unable to init ftdi scan device"（libusb_init 失败），
该输出证明二进制可执行、依赖链加载成功。
"""
import os

from conan import ConanFile


class IndiNightscapeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["indi-nightscape"].package_folder
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # OHOS: /system/bin/sh (mksh) 无法执行 ELF，用 bash 包装 (2048.c 同款模式)
        self.run(f"{bash} test.sh {pkg}", env="conanrun")
