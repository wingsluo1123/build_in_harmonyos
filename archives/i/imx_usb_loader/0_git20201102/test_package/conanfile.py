#!/usr/bin/env python3
"""Conan test_package — imx_usb_loader（L1：消费者用例 + 交付形态自检）

本包交付的是两个 CLI 可执行体与一份配置数据库，没有可供链接的库，因此消费者
用例分两条腿：
  * test_consumer.py —— 真跑交付的 bin/imx_usb、bin/imx_uart（能执行就真跑，
    OHOS 上 conan 包目录内的动态链接 ELF 可能被加载器拒绝时**显式打印平台限制**），
    并按上游 imx_loader_config.c 的格式用独立 Python 解析器核对
    etc/imx-loader.d/imx_usb.conf 的 VID:PID 映射契约；
  * test_layout.py —— 交付形态自检（M），纯 Python 自解析 ELF。
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class ImxUsbLoaderTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # 交付的 imx_usb 在运行时需要找到 libusb-1.0.so.0（产物没有 RPATH）
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        imx = self.dependencies["imx_usb_loader"]
        pkg = imx.package_folder
        version = imx.ref.version

        self.run('python3 "{}" --package-folder "{}" --os "{}" --arch "{}"'.format(
            os.path.join(self.source_folder, "test_consumer.py"),
            pkg, self.settings.os, self.settings.arch), env="conanrun")

        self.run('python3 "{}" --package-folder "{}" --os "{}" --arch "{}" '
                 '--version "{}"'.format(
                     os.path.join(self.source_folder, "test_layout.py"),
                     pkg, self.settings.os, self.settings.arch, version), env="conanrun")

        # 鸿蒙特有测试（OHOS-native）：判据全部是鸿蒙平台特有的，只在 os=OHOS 上真跑；
        # 非 OHOS 构建由脚本**显式打印跳过原因**（本地复核可用 --os OHOS 强制跑全部判据）。
        self.run('python3 "{}" --package-folder "{}" --os "{}" --arch "{}"'.format(
            os.path.join(self.source_folder, "test_ohos_native.py"),
            pkg, self.settings.os, self.settings.arch), env="conanrun")
