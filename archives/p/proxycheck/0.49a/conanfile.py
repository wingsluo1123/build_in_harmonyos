#!/usr/bin/env python3
"""Conan recipe for proxycheck 0.49a - open proxy checker CLI (+ proxylogger).

上游 configure 是 Michael Tokarev 手写的 autoconf-*风格* 脚本（291 行，非 autoconf 生成）：
除 --help 外拒绝任何命令行选项（`unknown option` + exit 1），没有 --prefix，CC/CFLAGS/
LDFLAGS 只从环境变量读取；Makefile.in 没有 install 目标，`all:` 只建 proxycheck。
因此本配方按 archives/l/libudns/0.6（同一上游作者）的做法：就地 configure + make，再手动
staging 二进制与手册页。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class ProxycheckConan(ConanFile):
    name = "proxycheck"
    version = "0.49a"
    description = (
        "proxycheck - command line open proxy checker (SOCKS4/SOCKS5, HTTP "
        "CONNECT/POST/PUT, WINGATE, FTP) with the proxylogger inetd helper"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://www.corpit.ru/mjt/proxycheck.html"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _c_compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return compilers.get("c") or compilers.get("cpp")

    def build(self):
        apply_conandata_patches(self)
        cc = self._c_compiler()
        if not cc:
            raise ConanInvalidConfiguration(
                "C compiler executable is not configured"
            )
        work = self.source_folder
        # configure 只读环境里的 CC/CFLAGS/LDFLAGS，不接受任何选项参数。
        envline = f'CC="{cc}"'
        self.run(f'bash -c \'cd "{work}" && export {envline} && ./configure\'')
        # all: 只构建 proxycheck；proxylogger 需显式指定目标。
        self.run(
            f'bash -c \'cd "{work}" && export {envline} && '
            f'make -j2 proxycheck proxylogger\''
        )
        # 上游自带 event 层自检（event.c:919 的 #if TEST 块）：上游任何目标都不编译它，
        # 本配方显式编译并真实运行，作为注册进 build() 的上游测试项（补丁修正其过期回调签名）。
        self.run(
            f'bash -c \'cd "{work}" && export {envline} && '
            f'$CC -I. -D_GNU_SOURCE -D_BSD_SOURCE -DHAVE_CONFIG_H -DTEST '
            f'-o event_selftest event.c\''
        )
        # stdin 必须是管道：epoll 不接受 /dev/null（EPERM），故用 `printf x |` 让 io 回调
        # 真实被调用并回显，随后 EOF -> exit(0)。输出先落盘再断言，避免 grep -q 提前关闭
        # 管道给被测进程 SIGPIPE 的竞态。
        self.run(
            f'bash -c \'cd "{work}" && '
            f'printf x | timeout 20 ./event_selftest > .selftest.out && '
            f'grep -q "input: x" .selftest.out\''
        )

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        for tool in ("proxycheck", "proxylogger"):
            copy(
                self,
                tool,
                src=self.source_folder,
                dst=bindir,
                keep_path=False,
            )
        # 上游没有 install 目标，手册页按 section 手动 staging
        copy(
            self,
            "proxycheck.1",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "man", "man1"),
            keep_path=False,
        )
        copy(
            self,
            "event.3",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "man", "man3"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = []
        self.cpp_info.set_property("cmake_file_name", "proxycheck")
