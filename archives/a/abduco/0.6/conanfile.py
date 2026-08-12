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

    def source(self):
        # 显式下载解压并剥离顶层目录（get strip_root=True——GitHub archive
        # 的顶层目录 abduco-0.6/ 被剥离——源码文件【Makefile 等】直接到
        # source_folder 顶层——避免源码布局不确定【CI #21461 顶层无
        # Makefile / #21555 子目录不存在】）
        from conan.tools.files import get
        get(self, self.conan_data["sources"][self.version]["url"],
            sha256=self.conan_data["sources"][self.version]["sha256"],
            strip_root=True)

    def build(self):
        # abduco 无 configure（Makefile 直接构建——config.mk 默认 CC=cc，
        # OHOS 仅有 clang——显式传 CC=clang；-j1：OHOS 沙箱不支持
        # mkfifo（jobserver），并行编译失败（opensp/multitail 先例）。
        # cwd=self.source_folder（strip_root 后源码文件在顶层——
        # Makefile 在顶层——CI #21461/#21555 修复）
        self.run("make -j1 CC=clang", cwd=self.source_folder,
                 env="conanbuild")

    def package(self):
        # Makefile install 支持 DESTDIR+PREFIX（cp -f abduco
        # ${DESTDIR}${PREFIX}/bin + man page）——cwd 同 build（顶层）
        self.run("make install DESTDIR={} PREFIX=/usr".format(
            os.path.join(self.package_folder)), cwd=self.source_folder,
            env="conanbuild")

    def package_info(self):
        self.cpp_info.bindirs = ["usr/bin"]
