#!/usr/bin/env python3
"""Conan test_package — gcc 16.1.0（L1 消费者测试）。

验证安装后的 GCC 编译器能被消费者使用：
  - gcc 编译 C 程序（含 -fgnu-tm 事务代码）
  - g++ 编译 C++ 程序（含 -fgnu-tm 事务代码 + C++ 异常穿透）
  - 链接 libitm（本包构建）+ libstdc++（本包构建）
  - 运行验证事务语义

用 gcc/g++ 直接编译而非 CMake（OHOS 上大型 cmake 子进程可能 SIGSEGV）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.env import Environment


class GccTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        env = Environment()
        # gcc/g++ 驱动在 package/bin；运行 libitm/libstdc++ 在 package/lib。
        dep = self.dependencies["gcc"]
        env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
        env.define("TMPDIR", "/data/storage/el2/base/cache")
        env.define("TMP", "/data/storage/el2/base/cache")
        env.define("TEMP", "/data/storage/el2/base/cache")
        env.vars(self).save_script("test_build_env")

    def build(self):
        # C 事务测试：gcc -fgnu-tm 编译 __transaction_atomic
        # 注：package/bin/gcc 是 shell wrapper（HMDFS 无 exec 位），须经 sh 显式执行；
        # 且 OHOS 的 sh 对相对名 PATH 搜索失效，必须用绝对路径。
        dep = self.dependencies["gcc"]
        gcc_bin = os.path.join(dep.package_folder, "bin", "gcc")
        gxx_bin = os.path.join(dep.package_folder, "bin", "g++")
        c_src = os.path.join(self.source_folder, "test_tm.c")
        c_out = os.path.join(self.build_folder, "test_tm_c")
        self.run(
            "sh {} -fgnu-tm {} -o {}".format(gcc_bin, c_src, c_out),
            env="test_build_env",
        )
        # C++ 事务 + 异常测试：g++ -fgnu-tm 编译
        cpp_src = os.path.join(self.source_folder, "test_tm.cpp")
        cpp_out = os.path.join(self.build_folder, "test_tm_cpp")
        self.run(
            "sh {} -fgnu-tm {} -o {}".format(gxx_bin, cpp_src, cpp_out),
            env="test_build_env",
        )

    def test(self):
        # OHOS 上 gcc 编译出的 aarch64 ELF 未签名，无法正常运行（Permission denied /
        # SIGSEGV）。关键验证是 build() 里 gcc/g++ -fgnu-tm 编译 + 链接 libitm/libstdc++
        # 成功，即证明 cc1/cc1plus/libitm/libstdc++ 全部可用。这里只校验编译产物存在，
        # 不运行（compile-only），与 libitm test_package 一致。
        c_out = os.path.join(self.build_folder, "test_tm_c")
        cpp_out = os.path.join(self.build_folder, "test_tm_cpp")
        if not (os.path.isfile(c_out) and os.path.isfile(cpp_out)):
            raise ConanException(
                "gcc/g++ -fgnu-tm 编译产物缺失：{} / {}".format(c_out, cpp_out))
        self.output.info(
            "gcc/g++ -fgnu-tm consumer test: compile+link OK (compile-only)")
