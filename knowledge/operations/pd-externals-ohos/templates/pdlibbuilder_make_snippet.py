# pd-lib-builder 在 OHOS 上的配方片段（策略 A + B）
#
# 适用：上游用 pd-lib-builder（`Makefile.pdlibbuilder`）构建的 Pd 外部库。
# 复制到 conanfile.py 的 requirements()/build() 中即可；处方理由见
# knowledge/operations/pd-externals-ohos/README.md 第 1、4 节。
#
# 生产样例：archives/p/pd-vbap/1.2.1/conanfile.py（本拓展的样例库，已实测全绿）
#
# 片段依赖的 import：import os
#                   from conan.tools.files import copy

# ---- requirements() ---------------------------------------------------------
# 编译外部对象需要 **Pd 内部头**（vbap.c 直接 include "s_stuff.h"），
# 只有 puredata 包含这些头；libpd 包只装 include/libpd，缺 s_stuff.h。
# puredata 的 package_type = "application" 且 cpp_info.includedirs 为空，
# 因此路径必须用 package_folder + "include/pd" 拼出来。
def requirements(self):
    self.requires("puredata/0.54.1")          # Pd 头集（含 s_stuff.h / g_canvas.h / m_imp.h）
    self.test_requires("libpd/0.16.1")        # 消费者测试用 Pd 引擎（动态加载宿主）


# ---- build() ----------------------------------------------------------------
# 三处必须显式指定，缺一即红：
#   1) CC        —— OHOS 无 cc/gcc；pd-lib-builder 默认 CC = $(PLATFORM)-cc|gcc，
#                   且用 `$(CC) -dumpmachine` 探测三元组，取不到即在 Makefile.pdlibbuilder
#                   硬失败（实测 line 764: Command "cc -dumpmachine" did not return a
#                   target triplet, needed for a build）。
#                   编译器从 Conan 取（R33：禁止裸用 shell 的 ${CC}）。
#   2) PDINCLUDEDIR —— pd-lib-builder 的关键字（Makefile.pdlibbuilder: PDINCLUDEDIR ?= $(pdincludepath)）。
#   3) -j1       —— 依铁律 E525：OHOS 上统一单并发（避免宿主资源与竞态）。
def build(self):
    dep = self.dependencies["puredata"]
    pd_include = os.path.join(dep.package_folder, "include", "pd")
    # conf 里 compiler_executables 是整 dict（{"c": ..., "cpp": ...}），**没有 ':c' 子键**：
    # 直接取子键会抛 ConanException: [conf] 'tools.build:compiler_executables:c' does not
    # exist in configuration list（生产样例踩过），必须 check_type=dict 取 dict 再取 'c'。
    compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
    cc = compilers.get("c") or "clang"
    self.run(
        "make -j1 CC={cc} PDINCLUDEDIR={inc}".format(cc=cc, inc=pd_include),
        cwd=self.source_folder,
    )


# ---- package() --------------------------------------------------------------
# pd-lib-builder 的产物是 <lib.name>.pd_linux（外部对象，不是链接库）：
# 安装到 libdirs；headerdirs/其他按上游 datafiles 决定。
def package(self):
    # Conan 2 API：self.copy() 是 1.x 写法（已移除），须用 conan.tools.files.copy
    src = self.source_folder
    copy(self, "*.pd_linux", src=src, dst=os.path.join(self.package_folder, "lib"))
    copy(self, "*.h", src=src, dst=os.path.join(self.package_folder, "include"), keep_path=False)
    copy(self, "*.pd", src=src, dst=os.path.join(self.package_folder, "share"))
    copy(self, "README*", src=src, dst=os.path.join(self.package_folder, "share", "doc"))


# ---- package_info() ---------------------------------------------------------
# 外部对象由 Pd 宿主 dlopen，**不进 cpp_info.libs**（否则消费者会尝试 -lXXX 链接失败的符号）。
def package_info(self):
    self.cpp_info.libdirs = ["lib"]
    self.cpp_info.libs = []                   # 插件不是可链接库
