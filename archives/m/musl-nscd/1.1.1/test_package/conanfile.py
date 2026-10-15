#!/usr/bin/env python3
"""test_package for musl-nscd — 消费者视角的端到端测试。

R34：本测试真实执行被测包安装出的 `nscd` 守护进程，并通过 AF_UNIX socket
按 NSCD 二进制协议取回 passwd/group 条目；桩 NSS 模块 `#include <nss.h>`
（该头文件来自被测包），因此同时验证「可执行文件产物」与「头文件产物」。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import chdir


class MuslNscdTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _cc(self):
        # dict 型 conf：不能按 `:c` 子键取（未声明的 conf 名会抛异常）
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return compilers.get("c", "clang") if compilers else "clang"

    def _file(self, name):
        """定位 test_package 内的源文件（create/test 两种入口的 folder 语义不同）。"""
        for base in (self.source_folder, self.recipe_folder, self.build_folder):
            candidate = os.path.join(base, name)
            if os.path.isfile(candidate):
                return candidate
        return name

    def build(self):
        # 桩 NSS 模块（nscd 运行期 dlopen 加载）+ 协议客户端
        dep = self.dependencies[self.tested_reference_str]
        inc = os.path.join(dep.package_folder, "include")
        cc = self._cc()
        with chdir(self, self.build_folder):
            self.run(
                f'{cc} -O1 -Wall -Wextra -fPIC -shared -I"{inc}" '
                f'-o libnss_ohostest.so.2 "{self._file("nss_ohostest_module.c")}"'
            )
            self.run(f'{cc} -O1 -Wall -Wextra -o nscd_client "{self._file("nscd_client.c")}"')

    def test(self):
        if not can_run(self):
            return

        dep = self.dependencies[self.tested_reference_str]
        # OHOS 上 /bin/sh 可能是不适合执行 ELF 的 mksh，优先用 bash
        shell = os.environ.get("CONFIG_SHELL", "")
        if not shell or not os.path.isfile(shell):
            shell = shutil.which("bash") or "/bin/sh"

        env = Environment()
        env.define("NSCD_BIN", os.path.join(dep.package_folder, "sbin", "nscd"))
        env.define("TEST_BIN_DIR", self.build_folder)
        with env.vars(self, scope="run").apply():
            self.run(f'{shell} "{self._file("test.sh")}"', env="conanrun")
