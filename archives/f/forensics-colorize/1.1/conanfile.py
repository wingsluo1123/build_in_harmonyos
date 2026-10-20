#!/usr/bin/env python3
"""Conan recipe — forensics-colorize 1.1 (upstream: jessek/colorize) / OpenHarmony PC.

适配路径：路径 A（基础适配）—— 改动只落在 archives/f/forensics-colorize/1.1/，
上游源码与测试用例**零修改**。

上游是什么
----------
Jesse Kornblum 的取证小工具集 ``colorize`` 1.1（2013 年最后更新），autotools
（autoconf/automake）工程，两个命令行程序：

* ``colorize``    —— 把任意文件的字节流渲染成 24 位 BMP 图片（默认 100 字节宽），
                     用来 "看见" 文件结构（取证时比对文件头/尾部/填充区）；
* ``filecompare`` —— 按块比对两个文件，每块写一个字节到 stdout
                     （0x80 相同 / 0xFE 不同 / 0xFF 填充），可再喂给 colorize 渲染。

包名取 ``forensics-colorize``：与平台任务 #15244、archives/f/forensics-colorize
目录一致（CI L0m-4 要求 conanfile.name == 目录名）。不取 ``colorize`` 是因为
conan/ConanCenter 上已有同名包（Ruby 终端着色工具），会撞名。

构建形态：为什么不走 autotools / conan_toolchain
------------------------------------------------
1. 上游只有 autotools。conan 的 ``AutotoolsToolchain`` 需要 autoconf/automake
   参与（bootstrap.sh），而这两者是构建机工具，CI worker 与本机不保证齐备；
   上游 1.1 的源码根本没有 configure 产物（release tag 里只有 configure.ac）。
2. 因此直接调用 profile 注入的 clang，按上游 src/Makefile.am **逐字相同**的
   源文件集合编译（不合并成库：colorize.c 与 filecompare.c 各自有 main() 且
   均 ``typedef struct _state``，上游本来就是两个独立程序）。
3. 上游需要的 config.h 由 ohos-compat/config-defs.h 提供（``-include``，
   位置等价于 autoconf 的 config.h）；``__progname`` 在非 glibc 平台上的
   重复定义问题由 ohos-compat/config-shim.h 解决。两者都不改源码，细节见各自
   文件头。
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get

# 与上游 src/Makefile.am 的 COMMON_SRC / colorize_SOURCES / filecompare_SOURCES 一一对应
COMMON_SRC = ["ui.c", "helpers.c"]
PROGRAMS = {
    "colorize": ["colorize.c"],
    "filecompare": ["filecompare.c"],
}
# helpers.c 是 __progname 唯一强定义的所在 TU（见 ohos-compat/config-shim.h）
PROGNAME_TU = "helpers.c"


class ForensicsColorizeConan(ConanFile):
    name = "forensics-colorize"
    version = "1.1"
    description = (
        "Forensic byte-stream visualiser: render any file into a BMP image and "
        "compare two files block by block (upstream jessek/colorize)"
    )
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/jessek/colorize"
    url = ""
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # 上传 ohos-compat/ 与 test_package/（无 patches/）
        copy(self, "ohos-compat/*", src=self.recipe_folder,
             dst=self.export_sources_folder)
        copy(self, "test_package/*", src=self.recipe_folder,
             dst=self.export_sources_folder)

    def source(self):
        # codeload URLs end in the tag name (e.g. ".../tar.gz/refs/tags/release-1.1")
        # which has no file extension, so Conan's get() deduces filename
        # "release-1.1" and unzip() falls back to the zip decoder -> BadZipFile
        # (实测 2026-10-18: "ERROR: ... BadZipFile: File is not a zip file").
        # Pass an explicit *.tar.gz filename so unzip() selects the tar.gz decoder.
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="colorize-release-1.1.tar.gz")

    # ── 工具链 ────────────────────────────────────────────────────────────
    def _compiler(self):
        """host 侧 C 编译器：profile 的 tools.build:compiler_executables.c。

        与同仓其它 autotools 配方一致：CI worker / 鸿蒙 PC 原生构建语义下
        PATH 里没有 ``cc``/``gcc``，必须用 conan 注入的绝对路径。
        """
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c")
        if not cc:
            raise ConanException(
                "profile 缺少 tools.build:compiler_executables.c（OHOS 原生构建必需）"
            )
        return cc

    def _flags(self):
        src = self.source_folder
        compat = os.path.join(self.source_folder, "ohos-compat")
        return " ".join([
            "-O2",
            "-g",
            "-Wall",
            f'-I"{os.path.join(src, "src")}"',
            # main.h 在非 glibc 时直接定义 __progname；先改名再让 shim 统一成
            # 「helpers.c 强定义 + 其余 TU 弱定义」，见 ohos-compat/config-shim.h
            "-D__progname=__fc_progname__",
            # 等价于上游 config.h（先于 main.h 生效）
            f'-include "{os.path.join(compat, "config-defs.h")}"',
            f'-include "{os.path.join(src, "src", "main.h")}"',
            f'-include "{os.path.join(compat, "config-shim.h")}"',
        ])

    def build(self):
        cc = self._compiler()
        src = os.path.join(self.source_folder, "src")
        flags = self._flags()

        # 与 autotools 一样先编 .o 再链接（同名符号问题在编译期就能暴露，
        # 不会因为“一步到底”掩盖某个 TU 的失败）
        for program, extra in PROGRAMS.items():
            objects = []
            for name in COMMON_SRC + extra:
                obj = os.path.join(self.build_folder, f"{program}-{name}.o")
                extra_def = (
                    " -DFORENSICS_COLORIZE_PROGNAME_TU" if name == PROGNAME_TU else ""
                )
                self.run(
                    f'"{cc}" {flags}{extra_def} -c -o "{obj}" '
                    f'"{os.path.join(src, name)}"',
                    cwd=self.build_folder,
                )
                objects.append(f'"{obj}"')
            self.run(
                f'"{cc}" -o "{os.path.join(self.build_folder, program)}" '
                + " ".join(objects),
                cwd=self.build_folder,
            )

    # ── 打包 ──────────────────────────────────────────────────────────────
    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        for program in PROGRAMS:
            binary = os.path.join(self.build_folder, program)
            if not os.path.isfile(binary):
                raise ConanException(f"{program} 未生成：{binary}")
            shutil.copy2(binary, os.path.join(bindir, program))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", self.name),
             keep_path=False)

    def package_info(self):
        # 命令行工具：两个可执行文件装在 bin/；commands.json 在软件级目录声明（CI L0k）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
