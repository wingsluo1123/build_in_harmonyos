#!/usr/bin/env python3
"""Conan recipe for qabc 1.16 (Qt6 qmake GUI, HarmonyOS PC aarch64).

qabc 是 ABC 乐谱最小 GUI（Qt6 Widgets，qmake 工程）。OHOS 适配要点：
- Qt6 依赖：qtbase/6.11.1 提供 Core/Gui/Widgets；翻译编译工具 lrelease
  由 qttools/6.11.1 提供（qtbase 包不含 LinguistTools）。
- 构建：qtbase 包内 qmake6 + make；QMAKE_LRELEASE 显式指到 qttools 的
  lrelease（qabc.pro 默认 $$[QT_INSTALL_BINS]/lrelease 在 qtbase 包内
  不存在）。
- 运行期库：qtbase/qttools 的 host 工具（qmake6/lrelease）是 OHOS 本机
  ELF，DT_NEEDED 含 libc++_shared.so，只有 OHOS SDK 提供（llvm/lib/
  aarch64-linux-ohos/），需注入 LD_LIBRARY_PATH（fingerterm 同款处理）。
- 打包：纯可执行包（无 lib/ 产物）。OHOS hmdfs 上 strip 后的 ELF 无法
  执行（Operation not permitted），因此直接复制未 strip 的二进制。
- 运行时外部工具（abc2midi/abcm2ps/fluidsynth/zathura）为可选功能，
  README 声明缺省时退化为纯文本编辑器，不影响编译与主界面功能。
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class QabcConan(ConanFile):
    name = "qabc"
    version = "1.16"
    description = "ABC music notation minimal GUI (Qt6)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/be1/qabc"
    url = "https://github.com/be1/qabc"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6：Core/Gui/Widgets 由 qtbase 提供；lrelease（翻译编译）由
        # qttools 提供（qtbase 包内无 LinguistTools 工具）。
        self.requires("qtbase/6.11.1", transitive_headers=True, transitive_libs=True)
        self.requires("qttools/6.11.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # qmake6/lrelease 是 OHOS 本机 ELF，运行期需要 Qt 动态库与 SDK
        # libc++_shared.so 才能解析自身 DT_NEEDED（fingerterm 同款）。
        env = Environment()
        for sdk_lib in self._ohos_sdk_lib_dirs():
            env.prepend_path("LD_LIBRARY_PATH", sdk_lib)
        for pkg in ("qtbase", "qttools"):
            dep = self.dependencies[pkg]
            if dep and dep.package_folder:
                env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        env.vars(self).save_script("conanbuild_qt_libs")

    @staticmethod
    def _ohos_sdk_lib_dirs():
        """Locate OHOS SDK llvm lib dirs providing libc++_shared.so.

        qtbase/qttools 的 host 工具（qmake6/lrelease）是 OHOS 本机 ELF，
        DT_NEEDED 含 libc++_shared.so；只有 OHOS SDK 提供该库
        （llvm/lib/aarch64-linux-ohos/）。glob 覆盖全部已安装 SDK 版本，
        不硬编码具体版本目录（fingerterm 先例首项硬编码，此处按 W4
        审计意见去除）。
        """
        dirs = []
        for cand in sorted(
            glob.glob(
                "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib/aarch64-linux-ohos"
            )
        ):
            if os.path.isdir(cand) and cand not in dirs:
                dirs.append(cand)
        return dirs

    def _toolchain_bin_dirs(self):
        """Locate compiler bin dirs that must be on PATH for qmake.

        qmake 生成 Makefile 时会探测 CC/CXX（mkspec 默认裸名 clang/clang++），
        该探测通过 PATH 查找编译器；CI 构建环境不保证编译器目录在 PATH 中
        （CMake 类配方用 conf 里的绝对路径，qmake 类配方必须显式注入），
        否则报 `Project ERROR: Cannot run compiler 'clang++'`。
        优先取 profile conf tools.build:compiler_executables 的目录，
        并兜底 glob OHOS SDK bin 与 HNP bin。
        """
        dirs = []
        compilers = self.conf.get("tools.build:compiler_executables") or {}
        if isinstance(compilers, dict):
            for key in ("c", "cpp"):
                path = compilers.get(key)
                d = os.path.dirname(path) if path else ""
                if d and d not in dirs:
                    dirs.append(d)
        for cand in sorted(
            glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin")
        ) + ["/data/service/hnp/bin"]:
            if os.path.isdir(cand) and cand not in dirs:
                dirs.append(cand)
        return dirs

    def build(self):
        apply_conandata_patches(self)
        qtbase = self.dependencies["qtbase"].package_folder
        qttools = self.dependencies["qttools"].package_folder
        qmake = os.path.join(qtbase, "bin", "qmake6")
        if not os.path.isfile(qmake):
            qmake = os.path.join(qtbase, "bin", "qmake")
        lrelease = os.path.join(qttools, "bin", "lrelease")
        qtlib = os.path.join(qtbase, "lib")
        src = self.source_folder

        # 构建环境（R33：不依赖未定义的 shell 环境变量，全部在 Python 内计算）：
        # - PATH：qmake 生成 Makefile 时会探测 CC/CXX（默认裸名 clang/clang++），
        #   必须能通过 PATH 找到编译器；CI 构建环境不保证编译器目录在 PATH
        #   中（CMake 类配方用绝对路径，qmake 类配方须显式注入），否则报
        #   `Project ERROR: Cannot run compiler 'clang++'`。
        # - LD_LIBRARY_PATH：qmake6/lrelease 及 make 生成的编译器调用是 OHOS
        #   本机 ELF，运行期需要 SDK libc++（llvm/lib/aarch64-linux-ohos）与
        #   Qt 动态库。
        env = Environment()
        env.define("QT_INSTALL_LIBS", qtlib)
        for bin_dir in self._toolchain_bin_dirs():
            env.prepend_path("PATH", bin_dir)
        for sdk_lib in self._ohos_sdk_lib_dirs():
            env.prepend_path("LD_LIBRARY_PATH", sdk_lib)
        env.prepend_path("LD_LIBRARY_PATH", qtlib)
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(qttools, "lib"))

        with env.vars(self).apply():
            self.run(
                f'{qmake} -config release "QMAKE_LRELEASE={lrelease}" {src}/qabc.pro',
                cwd=src,
            )
            # qmake 生成的 Makefile 中 man 页压缩规则用 GNU 专属的
            # `gzip --to-stdout`；CI 环境 gzip 为 toybox（OHOS 系统工具，
            # 不支持该选项），统一替换为可移植的 `gzip -c`（GNU/toybox
            # 均支持），否则 make 生成 qabc.1.gz 时报 Unknown option。
            makefile = os.path.join(src, "Makefile")
            with open(makefile, "r", encoding="utf-8", errors="replace") as fh:
                mk = fh.read()
            mk = mk.replace("gzip --to-stdout", "gzip -c")
            with open(makefile, "w", encoding="utf-8") as fh:
                fh.write(mk)
            self.run("make -j1", cwd=src)

    def package(self):
        src = self.source_folder
        # 可执行文件：直接复制未 strip 的二进制（OHOS hmdfs 上 strip 后
        # ELF 无法执行，绕过 make install 的 strip 环节）
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        shutil.copy2(os.path.join(src, "qabc"), os.path.join(bin_dir, "qabc"))
        os.chmod(os.path.join(bin_dir, "qabc"), 0o755)

        # 翻译文件（qmake 构建产物在源码树 locale/ 下）
        locale_dir = os.path.join(self.package_folder, "share", "qabc", "locale")
        os.makedirs(locale_dir, exist_ok=True)
        for qm in ("qabc_en.qm", "qabc_fr.qm"):
            p = os.path.join(src, "locale", qm)
            if os.path.isfile(p):
                shutil.copy2(p, os.path.join(locale_dir, qm))

        # 应用数据（desktop/icon/mime/metainfo）
        share = os.path.join(self.package_folder, "share")
        for dst, f in (
            (os.path.join("applications"), "qabc.desktop"),
            (os.path.join("icons", "hicolor", "scalable", "apps"), "qabc.svg"),
            (os.path.join("mime", "packages"), "qabc.xml"),
            (os.path.join("metainfo"), "fr.free.brouits.qabc.metainfo.xml"),
        ):
            d = os.path.join(share, dst)
            os.makedirs(d, exist_ok=True)
            p = os.path.join(src, f)
            if os.path.isfile(p):
                shutil.copy2(p, os.path.join(d, f))

    def package_info(self):
        # 纯可执行包（GUI/Qt6），无 lib/ 产物：不声明 cpp_info.libs
        # （kapow 先例：声明不存在的库会让 CMakeDeps 生成缺失 target）。
        self.cpp_info.bindirs = ["bin"]
        # 可执行程序包：将 bin 目录注入运行环境 PATH
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))