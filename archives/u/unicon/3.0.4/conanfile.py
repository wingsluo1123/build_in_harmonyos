#!/usr/bin/env python3
"""Conan recipe — unicon 3.0.4（custom 构建系统：自制 configure + Makefile.in）。

unicon 是 1990s 中文输入法框架：
  - server: libimm_server.so（进程内形态）/ imm_server（TCP 守护形态）
  - client: libimmclient.a
  - modules: cce（拼音/行内）、cxterm、turbo（.so，server dlopen 加载）
  - data: ccedata/gbdata/big5data 三件套在构建期用 unicon 主程序生成

无第三方依赖（requires 为空）：pth 已移植为 pthread，X11 残留已删，
tools/unikey/fonts 子目录随顶层 Makefile.in 摘除。
"""
import os

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, chdir, copy,
                               export_conandata_patches, get, rm, rmdir)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class UniconConan(ConanFile):
    name = "unicon"
    version = "3.0.4"
    description = ("unicon Chinese input method framework (server/client "
                   "libraries + cce pinyin module + input data)")
    license = "GPL-2.0"
    homepage = "https://sourceforge.net/projects/unicon/"
    url = ""  # CI fills this
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    # conan 2 对 package_type=library 强制要求 shared 选项；
    # 本包为固定构建（同时产出 libimm_server.so + libimmclient.a），选项仅作包模型声明
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 无第三方依赖：pthread/dl 为系统库
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33：编译器/标志取自 Conan Toolchain（conanbuild 环境）；
        # Makefile.in 的 CC/CXX 已环境变量化（见 patches 构建层修改）
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        with chdir(self, self.source_folder):
            self.run(f"./configure --prefix={self.package_folder}")
            self.run("make")
            # 数据三件套：用树内已构建的 unicon 二进制生成 sys-*.tab / dict 数据
            # （OHOS 原生构建，构建机可直接执行）
            self.run("make -C unicon ccedata gbdata big5data")

    def package(self):
        with chdir(self, self.source_folder):
            self.run("make install")
            # 上游 install 目标不装 dict 数据（install: all 只装库与模块 .so）；
            # cce inputs（*.tab/pinyin.map/*.def）与 turbo gb/gbk/big5 数据
            # 走独立的 data-install 目标
            self.run("make data-install")
        # 上游 install 目标不安装头文件：从源码树补拷
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "unicon", "include"),
             dst=os.path.join(self.package_folder, "include"))
        # 包为纯库类型：不发行可执行文件（避免 R38 commands.json 要求）
        for exe in ("unicon", "imm_server"):
            rm(self, exe, os.path.join(self.package_folder, "bin"))
        tools_dir = os.path.join(self.package_folder, "lib", "unicon", "bin")
        for tool in ("cin2dat", "cin2tab", "tab2cin", "tab2dat",
                     "tab2txt", "tab2txt1", "txt2tab", "txt2tab1"):
            rm(self, tool, tools_dir)
        rmdir(self, tools_dir)
        rm(self, "load-unimap.sh",
           os.path.join(self.package_folder, "lib", "unicon"))
        rmdir(self, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib/unicon"]
        # immclient: 客户端静态库（__DLL_SUPPORT__ 进程内形态）
        # imm_server: 服务端共享库（进程内形态提供 LibOpen/LibRelease）
        self.cpp_info.libs = ["immclient", "imm_server"]
