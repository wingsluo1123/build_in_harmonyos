#!/usr/bin/env python3
"""Conan test_package — kamailio-xhttp_prom L1 消费者用例。

xhttp_prom.so 是 kamailio 的插件模块，由 kamailio 二进制在运行期 loadmodule
（dlopen）加载。故本测试不以"文件是否存在"为终点，而是构造一个真实的消费者进程：
按 kamailio 模块加载器的两步序列加载模块（dlopen → dlsym exports → 解析导出表 →
dlsym mod_register 并实际调用），再叠加鸿蒙平台侧核对。

测试构成（共 33 项断言，全部通过才算 L1 通过）：
  1) consumer（C 程序）：运行期真实加载 + 导出表解析 + 平台符号归属核对（17 项）
     由 gen_shim.py 生成 kamailio 核心符号 shim 后编译成独立进程
  2) check_artifact.py：产物合规 + 鸿蒙平台适配核对（16 项）
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException


class KamailioXhttpPromTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _package_folder(self):
        return self.dependencies[self.tested_reference_str].package_folder

    def _module_path(self):
        return os.path.join(self._package_folder(), "lib", "kamailio", "modules",
                            "xhttp_prom.so")

    def _workdir(self):
        # test_package 的 build_folder 即 test_package 源目录，编译中间产物不能散落
        # 在这里；统一放 build-release/（.gitignore 已登记该路径，conan create 每次重生），
        # 并在 build() 起始与 test() 结束各清理一次，保证归档树始终只有源文件
        return os.path.join(self.build_folder, "build-release")

    def build(self):
        module = self._module_path()
        if not os.path.isfile(module):
            raise ConanException(f"xhttp_prom.so not found at {module}")

        # R33：编译器取自 Conan 配置，不使用未定义的 shell 环境变量
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c") or "clang"

        work = self._workdir()
        shutil.rmtree(work, ignore_errors=True)   # 清理上次残留
        os.makedirs(work, exist_ok=True)

        # 生成 kamailio 核心符号 shim（模块未定义符号的占位定义，供消费者进程
        # dlopen 时满足 -z now 全量重定位；占位符本身不会被调用）
        shim = os.path.join(work, "kamailio_core_shim.c")
        gen = os.path.join(self.source_folder, "gen_shim.py")
        self.run(f'"{sys.executable}" -B "{gen}" "{module}" "{shim}"')

        # 编译消费者进程：-rdynamic 使 shim 符号进入动态符号表供模块解析
        self._consumer = os.path.join(work, "consumer")
        src = os.path.join(self.source_folder, "consumer", "consumer.c")
        inc = os.path.join(self.source_folder, "consumer")
        self.run(f'"{cc}" -o "{self._consumer}" "{src}" "{shim}" -I"{inc}" -rdynamic')

    def test(self):
        module = self._module_path()
        checker = os.path.join(self.source_folder, "check_artifact.py")
        try:
            # R34 实质验证：真实加载模块 + 解析导出表 + 调用加载器钩子
            self.run(f'"{self._consumer}" "{module}"')
            # 鸿蒙平台适配与产物合规核对（-B：不生成 __pycache__）
            self.run(f'"{sys.executable}" -B "{checker}" "{module}"')
        finally:
            shutil.rmtree(self._workdir(), ignore_errors=True)
