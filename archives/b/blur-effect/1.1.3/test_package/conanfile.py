#!/usr/bin/env python3
"""test_package for blur-effect — 实际执行被测包二进制 blur_image（R34/R51）。

上游 1.1.3 无测试（N_static=0，清点证据见 ../notes.md「R51 上游测试清点」
与 test_package/MANIFEST.yml），鸿蒙侧补全：对真实 PNG 输入执行端到端离屏
高斯模糊渲染，校验输出文件生成、为合法 PNG、尺寸不变且内容确已变化。
"""
from conan import ConanFile
from conan.tools.build import can_run


class BlurEffectTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # bash 而非 sh：test.sh 依赖 set -o pipefail（非 POSIX）
            self.run("bash test.sh", env="conanrun", cwd=self.source_folder)
