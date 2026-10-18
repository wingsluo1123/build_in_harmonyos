#!/usr/bin/env python3
"""Conan recipe for uanytun 0.3.7 — tiny single-threaded SATP client.

uAnytun 是 SATP（Secure Anycast Tunneling Protocol）的精简实现，随源码自带
一个手写的 ``src/configure`` 脚本（非 autotools），构建产物是命令行工具
``uanytun``（上游默认安装到 <prefix>/sbin）。
"""
import os

from conan import ConanFile
from conan.tools.files import get
from conan.tools.layout import basic_layout


class UanytunConan(ConanFile):
    name = "uanytun"
    version = "0.3.7"
    description = ("uAnytun - tiny single-threaded implementation of the "
                   "Secure Anycast Tunneling Protocol (SATP)")
    license = "GPL-3.0-or-later"
    homepage = "https://www.anytun.org/"
    url = "https://www.anytun.org/"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        # 上游 configure 默认 --use-gcrypt；OHOS 制品仓已有 libgcrypt 及其
        # 传递依赖 libgpg-error 的 arm64 预编译包。
        self.requires("libgcrypt/1.11.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        src_dir = os.path.join(self.source_folder, "src")

        # 上游 configure 是手写 shell 脚本，把环境变量 CFLAGS/LDFLAGS 原样拼进
        # include.mk：`CFLAGS=$CFLAGS'-g -O2'` —— 拼接处没有空格，所以传入值
        # 必须以空格结尾，否则会粘成 `-I<dir>-g`（clang 报 gcrypt.h not found）。
        # 依赖头/库目录取自已解析的依赖图（含 libgpg-error 这类传递依赖）。
        includes, libdirs = [], []
        for dep in self.dependencies.values():
            includes.extend("-I" + path for path in dep.cpp_info.includedirs)
            libdirs.extend("-L" + path for path in dep.cpp_info.libdirs)
        os.environ["CFLAGS"] = " ".join(includes) + " "
        os.environ["LDFLAGS"] = " ".join(libdirs) + " "

        # configure 会按 --use-clang 把 include.mk 的 CC 写死成裸 `clang`；
        # 编译器路径从 conan 配置读取（R33：不引用未定义的 shell 变量），
        # 再用 make 命令行覆盖 include.mk 里的赋值。
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compiler_executables.get("c", "clang")
        jobs = self.conf.get("tools.build:jobs",
                             default=os.cpu_count() or 2, check_type=int)

        configure_args = [
            "./configure",
            "--target=Linux",
            "--prefix={}".format(self.package_folder),
            "--use-clang",
            # 手册页由上游 Makefile 经 asciidoc 重新生成，CI 无 asciidoc；
            # 示例配置只是 etc/uanytun 下的样例，随包无价值，一并关掉。
            "--no-manpage",
            "--no-examples",
        ]
        self.run(" ".join(configure_args), cwd=src_dir)
        self.run("make -j{} CC={}".format(jobs, cc), cwd=src_dir)

    def package(self):
        # configure 已把 prefix 指向 package_folder，make install 直接落到
        # <pkg>/sbin/uanytun 与 <pkg>/etc/{uanytun,init.d}（上游安装布局）。
        self.run("make install", cwd=os.path.join(self.source_folder, "src"))

    def package_info(self):
        self.cpp_info.bindirs = ["sbin"]
        self.cpp_info.libs = []
