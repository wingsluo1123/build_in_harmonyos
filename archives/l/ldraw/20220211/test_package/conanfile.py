#!/usr/bin/env python3
"""Conan test_package — ldraw 20220211（数据资源包消费侧校验）。

数据包没有可执行产物，唯一的"消费"行为就是按 LDraw 生态惯例读取
安装后的零件库数据（parts/、p/、models/、LDConfig.ldr）。因此 test()
调起 test_ldraw.py，以第三方消费者视角校验：
  1. share/ldraw/ 存在且 parts/ 非空（官方完整库零件数 > 30000）
  2. 随机抽检零件文件：存在、可读、首行是 0 开头的 LDraw 元命令
  3. LDConfig.ldr 颜色定义存在且含常见颜色码（如 4=红色）
  4. 样例模型 models/ 存在
"""
import os
import sys

from conan import ConanFile


class LdrawTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["ldraw"]
        script = os.path.join(self.recipe_folder, "test_ldraw.py")
        self.run(f'python3 "{script}" "{dep.package_folder}"')
