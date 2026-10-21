#!/usr/bin/env python3
"""Conan recipe — wmjupiter 1.21

wmjupiter 是一个 X11 dockapp，用 64x64 窗口画出木星的四大伽利略卫星位置
（I/E/G/C 四个标签）与木星大红斑（GRS）过中天时刻。上游：Thomas Kuiper 的
Window Maker dockapp，现由 engerim42 维护在 GitHub
（https://github.com/engerim42/wmjupiter，tag `1.21`），LICENSE 为 BSD-3-Clause
（三条式 BSD；FreeBSD ports 记为 GPLv2/BSD3CLAUSE 双授权，本仓库 tag 归档内
只带 BSD 三条式文本，故取 BSD-3-Clause）。

构建系统：一个手写 GNU Makefile，没有 configure、没有 automake，也没有上游测试
（Makefile 只有 `all` / `clean` / `install` 三个目标，无 `check`/`test` 入口）。
源码只有两个翻译单元 `wmJupiter.c` + `xutils.c`（外加 xutils.h 与两个被
`#include` 进源码的位图资源），产物是单个可执行文件 `wmJupiter`。

Makefile 的两条规则决定了本配方的全部形态（一手取证见 notes.md）：

* 规则里**没有** `$(CPPFLAGS)`/`$(LDFLAGS)`：
      `.c.o:  $(CC) $(CFLAGS) -D$(shell echo \`uname -s\`) -c $< -o $*.o $(INCDIR)`
      `wmJupiter: $(CC) $(CFLAGS) $(SYSTEM) -o wmJupiter $^ $(INCDIR) $(LIBDIR) $(LIBS)`
  与 wmcube/1.0.2 那种"把 CPPFLAGS/LDFLAGS 当自由通道"的 Makefile 不同，这里
  依赖目录没有环境变量入口，只能走 make 命令行变量覆盖。
* `CC`/`CFLAGS`/`INCDIR`/`LIBDIR`/`LIBS` 都是 Makefile 内部**赋值**，make 命令行
  同名变量会**替换**（而非追加）这些赋值。因此配方只接管 `CC`（硬编码的
  `gcc`）与两条陈旧的 X11R6 路径（`INCDIR=-I/usr/X11R6/include`、
  `LIBDIR=-L/usr/X11R6/lib`），`CFLAGS` 故意不覆盖以保留上游 `-O2 -Wall`，
  `LIBS` 也保留上游的 `-lXpm -lX11 -lXext -lm`（三者都被源码真实引用：
  XpmCreatePixmapFromData → libXpm、XShapeCombineMask → libXext、
  XOpenDisplay 系 → libX11、fabs 系 → libm）。

`make install` 不调用：上游 install 规则写成
`install -c -s -m 0755 wmJupiter $(DESTDIR)/bin`，`-s` 会就地 strip，且
`DESTDIR` 被 Makefile 赋成 `/usr/X11R6`；package() 用显式 copy 复现安装布局。

随包一个可移植性补丁对：xutils.h 里 7 个全局变量（跨 6 行 `extern` 声明）是**试探性定义**
（tentative definition，`Display *display;` 这种），wmJupiter.c 与 xutils.c
都 include 该头 ⇒ 每个 TU 各产生一份定义。1998 年的编译器把 common symbol
合并掉，clang 15 默认 `-fno-common` 则在链接期直接报
`ld.lld: error: duplicate symbol: display`（同类报错还出现在 win/NormalGC/
iconwin/screen/DisplayDepth）。修法按知识条目 E491 rec_priority 1：
头文件改 `extern` 声明（0002），把唯一定义放进 xutils.c（0001）。
E491 的 forbid_1 明确排除"加 `-fcommon` 全局放开"这条捷径。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout

_REQUIRED_SYSTEMS = ("Linux", "OHOS")


class WmjupiterConan(ConanFile):
    name = "wmjupiter"
    version = "1.21"
    description = ("X11 dockapp that tracks the positions of Jupiter's Galilean "
                   "moons and the central-meridian transit of the Great Red Spot")
    license = "BSD-3-Clause"
    homepage = "https://github.com/engerim42/wmjupiter"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 上游 LIBS = -lXpm -lX11 -lXext -lm，其中三个 X 库都被源码真实引用：
        #   XpmCreatePixmapFromData / XpmAttributes -> libXpm  (xutils.c, wmJupiter.c)
        #   XShapeCombineMask                       -> libXext (xutils.c)
        #   XOpenDisplay & friends                  -> libX11
        # `X11/extensions/shape.h` 由 xorgproto 提供，故显式要求。
        # 整张 X11 图统一在 cmd-pkgs 6.4.0 线上：libxpm/3.5.17 内部
        # `self.requires("libx11/6.4.0", force=True)`，把 libx11 钉到 1.8.x 会让
        # package_id 变化并触发 libxpm 源码重建（1.8.x 与 6.4.0 的 libX11.so.6
        # 不兼容，属已知雷区），所以这里逐项对齐 6.4.0。
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxext/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxpm/3.5.17", transitive_headers=True, transitive_libs=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)

    def validate(self):
        if str(self.settings.os) not in _REQUIRED_SYSTEMS:
            raise ConanInvalidConfiguration(
                f"wmjupiter supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # conanbuild 环境里仍有完整的 CPPFLAGS/LDFLAGS（供诊断与后续维护使用），
        # 只是本 Makefile 读不到它们，真正的注入在 build() 里用命令行变量完成。
        AutotoolsToolchain(self).generate()
        AutotoolsDeps(self).generate()

    @staticmethod
    def _join_dirs(flag, directories):
        """把目录列表拼成 `-Idir1 -Idir2` 形态，保持首次出现顺序并去重。"""
        seen, parts = set(), []
        for directory in directories:
            if directory and directory not in seen:
                seen.add(directory)
                parts.append(f"{flag}{directory}")
        return " ".join(parts)

    def _dependency_dirs(self):
        """收集所有依赖（含传递依赖）的头文件与库目录。"""
        includedirs, libdirs = [], []
        for dep in self.dependencies.values():
            cppinfo = dep.cpp_info.aggregated_components()
            includedirs.extend(cppinfo.includedirs)
            libdirs.extend(cppinfo.libdirs)
        return includedirs, libdirs

    def build(self):
        # 应用 conandata.yml 里登记的可移植性补丁对（试探性定义 -> extern + 单一定义）。
        apply_conandata_patches(self)

        # R33：编译器取自 Conan conf（profile 里 C 条目名是 "c"），不读 shell 变量。
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c") or "clang"

        includedirs, libdirs = self._dependency_dirs()
        # make 命令行变量替换（不追加）Makefile 内部赋值，故：
        #   CC=...            覆盖硬编码的 `CC = gcc`
        #   INCDIR=.../LIBDIR=... 覆盖陈旧的 X11R6 路径，换成依赖的真实目录
        #   CFLAGS=           故意不传，保留上游 `-O2 -Wall`
        # R9：-j1（OBJS 共享同一目录，且只有两个 TU，并行无收益）。
        self.run(
            f'make -j1 CC="{cc}" '
            f'INCDIR="{self._join_dirs("-I", includedirs)}" '
            f'LIBDIR="{self._join_dirs("-L", libdirs)}"',
            env="conanbuild", cwd=self.source_folder,
        )

    def package(self):
        copy(self, "wmJupiter", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc",
                              f"wmjupiter-{self.version}"))

    def package_info(self):
        # 命令行/GUI 应用：不导出头文件与库，只交付 bin/ 与文档。
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
        self.conf_info.define("user.wmjupiter:bin", "wmJupiter")
