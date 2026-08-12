#!/usr/bin/env python3
import os
from conan import ConanFile
from conan.tools.layout import basic_layout


class AbducoConan(ConanFile):
    name = "abduco"
    version = "0.6"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    # 无外部依赖（abduco 为纯 C 终端会话管理工具——Makefile 构建）

    def layout(self):
        basic_layout(self)

    def build(self):
        # abduco 无 configure（Makefile 直接构建——config.mk 默认 CC=cc，
        # OHOS 仅有 clang——显式传 CC=clang；-j1：OHOS 沙箱不支持
        # mkfifo（jobserver），并行编译失败（opensp/multitail 先例）。
        # cwd 用源码子目录（GitHub archive 解压带顶层目录 abduco-0.6/
        # ——Makefile 在子目录——CI #21461 报 No targets/makefile found）
        self.run("make -j1 CC=clang",
                 cwd=os.path.join(self.source_folder, "abduco-0.6"),
                 env="conanbuild")

    def package(self):
        # Makefile install 支持 DESTDIR+PREFIX（cp -f abduco
        # ${DESTDIR}${PREFIX}/bin + man page）——cwd 同 build（源码子目录
        # abduco-0.6/——Makefile 所在）
        self.run("make install DESTDIR={} PREFIX=/usr".format(
            os.path.join(self.package_folder)),
            cwd=os.path.join(self.source_folder, "abduco-0.6"),
            env="conanbuild")

    def package_info(self):
        self.cpp_info.bindirs = ["usr/bin"]
