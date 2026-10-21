#!/usr/bin/env python3
"""Conan recipe — pixelize 2.0.0-git20220108.d1f9da9

pixelize — photomosaic builder（Paul Wilkins 2000-2009 / Jean-Christophe
Dubois 2020-2022，https://github.com/jcdubois/pixelize）：`make_db` 把一组
小图并入图像数据库 pic_db.dat（-r/--reset 重建），`pixelize` 以 GTK3 界面
（glade UI 经 tools/glade2c 内嵌为 C 字符串常量）或命令行模式（-i/-o/-m）
把任意输入图像重绘为由数据库小图拼接的马赛克。

上游为无 release tag 的快照 commit d1f9da98ed4074f55db7c5ab4f701d70437810a3
（2022-01-08；版本号 2.0.0 取自快照根 pixelize-2.0.0.lsm），与 Debian
pixelize_2.0.0~git20220108.d1f9da9 打包的同一上游点。

License: GPL-2.0-or-later（上游 LICENSE 为 GPLv2 全文；Debian 声明 GPL-2+）。

适配要点：
- 纯 Makefile 工程（无 configure、无 install 目标）：build() 直接
  `make -j1 CC=<conf>` 编出 pixelize + make_db（obj/、depend 与产物二进制
  全部生成在源码树 → in-source 构建，folders.build=""，vimpc 同款）；
- include/pixelize_model.h 由上游 tools/glade2c（Python2/3 兼容脚本）从
  glade/pixelize.glade 生成：build() 用 conan 自带解释器（sys.executable）
  预生成——构建环境无 clang-format（Makefile 生成规则里的 `clang-format -i`
  已由补丁 0001 移除；且预生成产物 mtime 新于 glade 输入，规则不再触发）；
- 补丁 0001 同时移除 `-Werror`（Debian patches/Don-t-build-with-Werror
  同源决策：上游按 GCC 开发期告警基线编码，clang 15 的 -Wall -Wextra
  告警基线不同，-Werror 会把可移植性告警升级为编译失败）；
- 依赖经 PkgConfigDeps 提供：Makefile 以反引号内嵌
  `pkg-config --cflags/--libs gtk+-3.0` + `--libs gmodule-2.0`（glib 配方
  按组件导出 gmodule-2.0.pc）；tool_requires pkgconf 提供 pkg-config
  可执行文件（VirtualBuildEnv 注入 PATH）；
- 无 install 目标：package() 手工拷贝 bin/{pixelize,make_db}、
  share/man/man1/*.1、licenses/LICENSE；
- 两二进制均为 GTK3 应用（package_type=application）：gtk 在本制品仓为
  broadway 后端（适配鸿蒙无原生显示系统），GUI 运行时需 broadwayd +
  浏览器；无头环境的 gtk_init 失败路径即 test_package 的负向断言点。
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class PixelizeConan(ConanFile):
    name = "pixelize"
    version = "2.0.0-git20220108.d1f9da9"
    description = ("photomosaic builder: make_db merges a set of small "
                   "images into an image database, the pixelize GTK3 GUI "
                   "(or -i/-o/-m command line mode) re-renders any input "
                   "image as a mosaic of database tiles")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/jcdubois/pixelize"
    url = "https://github.com/jcdubois/pixelize"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    # VirtualBuildEnv: tool_requires pkgconf 的 pkg-config 进 PATH
    generators = "VirtualBuildEnv"

    def validate(self):
        # R32: settings.os must accept Linux and OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Makefile: `pkg-config --cflags/--libs gtk+-3.0` + `--libs gmodule-2.0`
        self.requires("gtk/3.24.43")

    def build_requirements(self):
        # Makefile 以反引号内嵌 pkg-config 调用（CFLAGS/DFLAGS 展开与
        # depend 目标的 $(CC) -MM）→ 构建环境需要 pkg-config 可执行文件
        self.tool_requires("pkgconf/3.0.5")

    def layout(self):
        # in-source（vimpc 同款）：上游 Makefile 的 obj/、depend、
        # include/pixelize_model.h 与产物二进制全部相对源码树生成
        basic_layout(self)
        self.folders.build = ""
        self.folders.generators = "conan"

    def source(self):
        # GitHub 官方 commit 归档（上游无 release tag；R39：上游官方分发
        # 渠道；与 Debian 2.0.0~git20220108.d1f9da9 同一上游快照点）
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # gtk+-3.0.pc（gtk 配方 pkg_config_name）与 glib 组件导出的
        # gmodule-2.0.pc：Makefile 反引号里的 pkg-config 查询命中
        PkgConfigDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)

        # Step 1: 预生成 include/pixelize_model.h（glade UI → C 字符串
        # 常量头）。用 conan 自带 Python 跑上游 tools/glade2c：构建环境
        # 无 clang-format（补丁已移除该步骤）；生成物 mtime 新于 glade
        # 输入，Makefile 的生成规则不再触发。
        model_h = os.path.join(self.source_folder, "include", "pixelize_model.h")
        os.makedirs(os.path.dirname(model_h), exist_ok=True)
        ret = self.run(
            f"{sys.executable} tools/glade2c -i glade/pixelize.glade -o include/pixelize_model.h",
            cwd=self.source_folder)
        if ret != 0:
            raise ConanException(f"glade2c failed (rc={ret})")

        # Step 2: 交叉编译。CC 来自 profile conf（本地 WSL 为
        # /opt/lpk-fixed/clang，CI worker 为 /data/service/hnp/bin/clang）；
        # make 命令行变量覆盖 Makefile 的 `CC = gcc`。
        cc = self.conf.get("tools.build:compiler_executables", check_type=dict)["c"]
        # PKG_CONFIG_PATH 显式注入 generators_folder（PkgConfigDeps 生成的
        # gtk+-3.0.pc/gmodule-2.0.pc 所在；本 conan 的 PkgConfigDeps 不自动
        # 注入该变量——abiword-plugin-docbook/3.0.8 同款显式注入）。
        env = Environment()
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        with env.vars(self).apply():
            # R9/E074: make -j1（HMDFS 不允许 jobserver FIFO）
            ret = self.run(f"make -j1 CC={cc}", cwd=self.source_folder, env="conanbuild")
        if ret != 0:
            raise ConanException(f"make failed (rc={ret})")

    def package(self):
        # 上游 Makefile 无 install 目标：手工拷贝（E490：恢复执行位）
        bindir = os.path.join(self.package_folder, "bin")
        for binary in ("pixelize", "make_db"):
            copy(self, binary, src=self.source_folder, dst=bindir)
            os.chmod(os.path.join(bindir, binary), 0o755)
        copy(self, "*.1", src=os.path.join(self.source_folder, "man", "man1"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # pixelize/make_db 是双二进制 GUI/CLI 应用：无公开头文件/导入库
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
