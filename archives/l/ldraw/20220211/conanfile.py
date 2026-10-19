#!/usr/bin/env python3
"""Conan recipe — ldraw 20220211 (pure data resource package).

LDraw.org 官方零件库（LDraw Parts Library）：LEGO 零件的 LDraw 格式
几何定义数据（.dat 零件/基元文件）、颜色定义（LDConfig.ldr）与样例模型。

适配要点：
  * 纯数据包：无构建系统、无编译产物、无 CLI 工具
    （上游 complete.zip 内仅有零件数据文件与 Windows 时代的 mklist.exe，
     OHOS 目标不安装任何可执行产物 → R38 commands.json 不适用）。
  * 上游官方源为 library.ldraw.org（任务头声明的 github.com/ldraw/library
    404 不存在；官方站点 www.ldraw.org 已迁移到 library.ldraw.org）。
  * 官方 complete.zip 是滚动更新快照（版本号按发布日期命名，如
    20220211 对应 2022-02-11 快照；FreeBSD cad/ldraw 端口在 20220211
    时点记录其 SHA-256=632bff…，但官方站点现已不再单独提供该历史快照，
    当前可下载的官方制品即本配方 source() 所取文件，见 notes.md）。
  * 安装路径遵循 LDraw 生态惯例：share/ldraw/（parts/、p/、models/、
    LDConfig.ldr 等），供 LDraw 兼容应用（渲染/查看器）按标准库路径读取。
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, get, \
    export_conandata_patches
from conan.tools.layout import basic_layout


class LdrawConan(ConanFile):
    name = "ldraw"
    version = "20220211"
    description = ("LDraw.org Official Parts Library — LEGO 零件几何数据 "
                   "(LDraw 格式 .dat/.ldr) 数据资源包")
    license = "CC-BY-2.0"          # 官方库许可：CC BY 2.0（见 ldraw/CAreadme.txt）
    homepage = "https://library.ldraw.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 纯数据包：Conan 无 data 类型，取 unknown（仓库同类数据包先例一致）
    package_type = "unknown"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=False)

    def build(self):
        # 纯数据包：无编译步骤，仅应用补丁（当前无补丁）
        apply_conandata_patches(self)

    def package(self):
        src = self.source_folder          # <src>/ldraw/...
        ldraw_src = os.path.join(src, "ldraw")
        if not os.path.isdir(ldraw_src):
            raise Exception(f"ldraw/ 目录缺失: {ldraw_src}")
        dst = os.path.join(self.package_folder, "share", "ldraw")
        os.makedirs(dst, exist_ok=True)

        # 数据目录：零件/基元/样例模型（LDraw 库主体）
        for sub in ("parts", "p", "models"):
            s = os.path.join(ldraw_src, sub)
            if os.path.isdir(s):
                copy(self, "*", src=s, dst=os.path.join(dst, sub))
        # 顶层配置文件与许可/说明
        for name in ("LDConfig.ldr", "LDCfgalt.ldr", "LDConfig_TLG.ldr",
                     "Readme.txt", "CAreadme.txt", "CAlicense.txt",
                     "CAlicense4.txt"):
            p = os.path.join(ldraw_src, name)
            if os.path.isfile(p):
                copy(self, name, src=ldraw_src, dst=dst, keep_path=False)

        # 统计并输出安装结果（供 test_package 与日志追溯）
        n_parts = sum(len(f) for _, _, f in os.walk(os.path.join(dst, "parts")))
        n_p = sum(len(f) for _, _, f in os.walk(os.path.join(dst, "p")))
        self.output.info(f"installed: parts={n_parts}, p={n_p}, models=...")

    def package_id(self):
        # 纯数据包：与平台/编译器无关，单一 package_id
        self.info.clear()

    def package_info(self):
        # 纯数据包：无 include/lib/bin，显式置空；数据在 share/ldraw
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []
        self.cpp_info.resdirs = ["share/ldraw"]
        # 供下游按 LDraw 惯例定位库根（如 LDRAW_LIB_PATH）
        self.runenv_info.define_path("LDRAW_LIB_PATH",
                                     os.path.join(self.package_folder,
                                                  "share", "ldraw"))
