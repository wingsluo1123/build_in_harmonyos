#!/usr/bin/env python3
"""Conan recipe for pqiv 2.13.3 — powerful quick image viewer (GTK+3).

HarmonyOS PC (aarch64) adaptation:
- Build system: bare GNUmakefile + custom ``configure`` shell script
  (no autotools/CMake). The script only writes ``config.make``; it must be
  invoked through bash (it contains bashisms) and must NOT be handed any
  ``--host/--build/--target`` (native build=host, iron rule #0).
- GTK+3 stack comes from the ohpcd registry (``gtk/3.24.43``). That recipe
  builds GTK with the broadway backend only (x11/wayland disabled), so no
  X11/Wayland system libraries are required.
- Dependency discovery uses pkg-config; ``PkgConfigDeps`` generates a private
  ``.pc`` set in the generators folder which is injected via
  ``PKG_CONFIG_PATH`` for both ``configure`` and ``make``.
- Only the built-in ``gdkpixbuf`` backend is enabled (``--backends=gdkpixbuf``)
  so the optional poppler/spectre/wand/libav/libarchive/libwebp backends do not
  drag in further unpublished dependencies.
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    get, load, save, apply_conandata_patches, export_conandata_patches)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class PqivConan(ConanFile):
    name = "pqiv"
    version = "2.13.3"
    description = "Powerful quick image viewer (GTK+3, command line driven)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/phillipberndt/pqiv"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32: os 判断必须 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "os={} not supported (only Linux/OHOS)".format(self.settings.os))

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # GTK+3 stack from ohpcd. gtk/3.24.43 transitively pins
        # glib/2.84.0.1, cairo/1.18.4, cairo-gobject/1.18.4.2,
        # pango/1.50.14.1.1, gdk-pixbuf/2.44.6.1, atk/2.38.0.1.1,
        # fribidi/1.0.16 and libepoxy/1.5.10 — declare only the two modules
        # pqiv links against directly to avoid version conflicts.
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        self.requires("gdk-pixbuf/2.44.6.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ #
    #  helpers                                                           #
    # ------------------------------------------------------------------ #
    def _cc(self):
        """R33: 编译器从 Conan conf 获取，禁止裸用 shell 的 $CC。"""
        execs = self.conf.get("tools.build:compiler_executables", default={}) or {}
        return execs.get("c", "") or "clang"

    def _bash(self):
        """OHOS 的 /bin/sh 是 mksh，configure 含 bash 语法，必须用 bash 驱动。"""
        return os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

    def generate(self):
        # Makefile 通过 pkg-config 探测依赖 → 生成私有 .pc 集合
        PkgConfigDeps(self).generate()
        self._write_pc_shims()

    def _write_pc_shims(self):
        """PkgConfigDeps 只为 conan 组件（gtk+-3.0 / gio-2.0）生成 .pc，而 pqiv
        的 GNUmakefile 还按模块名直接要求 `gdk-3.0`（gtk 包内的 GDK 子模块）与
        `gio-unix-2.0`（glib 包内的 unix 子模块）。在此派生指向真实包目录的 shim，
        写入 generators_folder（私有前缀，不污染系统 pkg-config 目录）。"""
        gen = self.generators_folder
        gtk_pc = os.path.join(gen, "gtk+-3.0.pc")
        gdk_pc = os.path.join(gen, "gdk-3.0.pc")
        if os.path.isfile(gtk_pc) and not os.path.exists(gdk_pc):
            text = load(self, gtk_pc).replace("Name: gtk+-3.0", "Name: gdk-3.0", 1)
            save(self, gdk_pc, text)
        gio_pc = os.path.join(gen, "gio-2.0.pc")
        gio_unix_pc = os.path.join(gen, "gio-unix-2.0.pc")
        if os.path.isfile(gio_pc) and not os.path.exists(gio_unix_pc):
            m = re.search(r"^Version:\s*(.+)$", load(self, gio_pc), re.MULTILINE)
            version = m.group(1).strip() if m else "2.0"
            save(self, gio_unix_pc,
                 "Name: gio-unix-2.0\n"
                 "Description: GIO unix specific APIs (conan shim)\n"
                 "Version: {}\n"
                 "Requires: gio-2.0\n".format(version))

    # ------------------------------------------------------------------ #
    #  build()                                                           #
    # ------------------------------------------------------------------ #
    def build(self):
        apply_conandata_patches(self)
        cc = self._cc()
        pc_path = self.generators_folder
        bash = self._bash()
        # 原生 build=host：不给 configure 传 --host/--build/--target（铁律 #0）。
        # PKG_CONFIG_PATH/CC 以环境变量前缀注入，configure 只接受它自身定义的选项。
        # --backends=gdkpixbuf: 只启用内置 gdk-pixbuf 后端（最小依赖面）。
        self.run(
            "PKG_CONFIG_PATH={pc} CC={cc} {bash} ./configure "
            "--prefix=/ --gtk-version=3 --backends=gdkpixbuf".format(
                pc=pc_path, cc=cc, bash=bash),
            cwd=self.source_folder, env="conanbuild")
        jobs = os.cpu_count() or 4
        self.run(
            "PKG_CONFIG_PATH={pc} CC={cc} make -j{j}".format(
                pc=pc_path, cc=cc, j=min(jobs, 8)),
            cwd=self.source_folder, env="conanbuild")
        # ── 上游官方测试（必做）──
        # 上游 2.13.3 没有测试套件（源码树无 test/ 目录；.github/workflows/ci.yml
        # 的 "check" 步骤仅为 ./configure && make && ./pqiv --version）。
        # 因此这里复跑上游 CI 的等效检查命令。
        self._upstream_smoke_test()

    def _upstream_smoke_test(self):
        """复跑上游 CI 的 check 命令：./pqiv --version（失败即中止构建）。"""
        self.run(
            "PKG_CONFIG_PATH={pc} ./pqiv --version".format(pc=self.generators_folder),
            cwd=self.source_folder, env="conanrun")

    def package(self):
        self.run(
            "PKG_CONFIG_PATH={pc} CC={cc} make install DESTDIR={dst}".format(
                pc=self.generators_folder, cc=self._cc(), dst=self.package_folder),
            cwd=self.source_folder, env="conanbuild")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
