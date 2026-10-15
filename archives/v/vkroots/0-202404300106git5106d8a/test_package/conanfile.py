#!/usr/bin/env python3
"""test_package for vkroots — 消费者视角验证（R34：真实使用被测头文件）。

上游为零测试的 header-only 库，故本测试是补全测试：
  * build()  编译一个真实的最小 Vulkan layer（test_layer.cpp 使用
             VKROOTS_DEFINE_LAYER_INTERFACES / vkroots::VkDeviceDispatch 等接口）
  * test()   断言产物存在、架构正确、且确实导出了 vkroots 生成的 layer 入口点；
             并在可能时做运行期协商验证
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class VkrootsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        import glob

        def find(pattern):
            hits = [
                c for c in glob.glob(
                    # CMake 的 MODULE 库带 lib 前缀（libvkroots_consumer_layer.so）
                    os.path.join(self.build_folder, "**", pattern),
                    recursive=True)
                if os.path.isfile(c)
            ]
            return hits[0] if hits else None

        layer = find("*vkroots_consumer_layer*")   # 用例 A：layer 模块（.so）
        e2e = find("*vkroots_negotiate_e2e*")      # 用例 B：端到端可执行文件
        if not layer:
            raise ConanException(
                "用例A 产物未找到：编译阶段未产出 vkroots_consumer_layer")
        if not e2e:
            raise ConanException(
                "用例B 产物未找到：编译阶段未产出 vkroots_negotiate_e2e")

        # OHOS: /system/bin/sh (mksh) 无法执行 ELF，须用 bash 包装；
        # 脚本用绝对路径，避免依赖 test() 的当前工作目录
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.recipe_folder, "test.sh")
        self.run(f'{bash} "{script}" "{layer}" "{e2e}"', env="conanrun")
