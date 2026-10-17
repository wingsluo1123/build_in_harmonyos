#!/usr/bin/env python3
"""debian-cloud-images 0.0.9 test_package —— 纯数据包，无需编译。

test() 分两段（均真实执行被测包的交付产物）：
  ① 完整消费者用例 consumer_cloud_images.py —— 按 Debian 打包语义把交付数据消费一遍：
     control 的 `${debian-cloud-images-packages:Depends}` 占位符 → substvars 的
     `debian-cloud-images-packages:Depends=` 字段 → 展开为带 [arch] 限定的条目 →
     过滤出 OHOS PC（arm64）适用子集。
  ② 适配自检 test_cloud_images.py —— 交付产物完整性与数据一致性断言（M=16）。
"""

import os
import sys

from conan import ConanFile


class DebianCloudImagesTestConan(ConanFile):
    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["debian-cloud-images"]
        package_folder = dep.package_folder

        # ① 完整消费者用例（平台 rule12：鸿蒙特有测试需有真正跑通流程的端到端用例）
        consumer = os.path.join(self.source_folder, "consumer_cloud_images.py")
        self.run(f"{sys.executable} {consumer} {package_folder}")

        # ② 适配自检（M=15，非上游用例；上游 N=0）
        check = os.path.join(self.source_folder, "test_cloud_images.py")
        self.run(f"{sys.executable} {check} {package_folder}")
