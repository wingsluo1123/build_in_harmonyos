#!/usr/bin/env python3
"""pop-sound 5.5.1.r7.g25ea85d test_package —— 纯数据包，无需编译。

验证分两层（R34：测试必须实质依赖被测包）：
  1) consumer_soundtheme.py —— 端到端消费者用例：把 package_folder/share 当 XDG_DATA_DIRS，
     按 freedesktop Sound Theme 规范定位主题 → 解析 index.theme → 按事件名解析到 .oga
     并实际读取容器头（12 条事件用例，含 4 个 README 记录的别名事件）。
  2) test_pop_sound.py —— 适配自检 38 条（结构 8 + 上游样例逐条 25 + 鸿蒙特有 5）。
"""

import os
import sys

from conan import ConanFile


class PopSoundTestConan(ConanFile):
    # 资源包：无编译器、无 settings、无 build 步骤。

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["pop-sound"].package_folder

        consumer = os.path.join(self.source_folder, "consumer_soundtheme.py")
        self.run(f"{sys.executable} {consumer} {package_folder}")

        checker = os.path.join(self.source_folder, "test_pop_sound.py")
        self.run(f"{sys.executable} {checker} {package_folder}")
