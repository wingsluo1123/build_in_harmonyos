#!/usr/bin/env python3
"""Conan recipe — robocut 1.0.11（Qt5 qmake 绘图仪/刻字机控制 GUI 应用，HarmonyOS PC aarch64）。

上游: https://github.com/Timmmm/robocut （tag v1.0.11, 2015；GPL-3.0+）
构建系统: qmake（Robocut.pro）+ make
依赖: qt5-qtbase/5.15.2.2（Core/Gui/Widgets）、qt5-qtsvg/5.15.2.1（QSvgRenderer）、
      libusb/1.0.29（libusb_bulk_transfer 访问切割机 USB 端点）

OHOS 适配要点（全部在配方层，不改上游源码）:
  - 上游 Robocut.pro 声明 `QT += svg`。ohpcd 的单包 qt/5.15.19 是 `-skip qtsvg`
    构建（无 Qt5Svg）→ 改用模块化栈 qt5-qtbase + qt5-qtsvg。
  - qt5-qtsvg 的 recipe 精确声明 qt5-qtbase/5.15.2，而带 Widgets 的是
    5.15.2.2 → override 统一到 5.15.2.2（baka 2.0.4 先例，补丁版本 API 兼容）。
  - qt5-qtbase / qt5-qtsvg 包内 mkspecs 记录的是**构建时**绝对路径（conan 缓存里
    构建目录已删除）：
      · bin/qt.conf 的 DevicePaths/Paths/HostPrefix 指向已消失的构建目录；
      · mkspecs/modules/qt_lib_*.pri 转发 include 到已消失的 modules-inst →
        qmake 直接报 `Unknown module(s) in QT: core gui`。
    → `_relocated_qmake()` 复制 mkspecs 到本包 build 目录、用 modules-inst 覆盖
      modules 转发件、注入 qtsvg 的 svg 模块，并写一份指向 package 的 qt.conf，
      qmake 即从 package 目录解析库/头文件/工具（qsoas 3.3 先例 + baka 2.0.4 的
      svg 模块处理）。
      qt_config.prf 在加载每个模块前把 $$QT_MODULE_*_BASE 统一设为
      $$[QT_INSTALL_*]（= qtbase 包），故 svg 模块须把这几项固化为 qtsvg 包路径，
      否则 qt.prf 会生成指向 qtbase 的 `libQt5Svg.so` 绝对路径。
  - 上游 `#include <libusb-1.0/libusb.h>` + `LIBS += -lusb-1.0`：libusb 包的
    includedirs 是 include/libusb-1.0（面向 `#include <libusb.h>` 消费者），
    上游写法多一层 → CPATH 补 <libusb>/include；链接 -lusb-1.0 走 LIBRARY_PATH。
  - QMAKE_STRIP=""：qmake 默认链接/安装规则会调用 strip，HMDFS 上被剥离的 ELF
    不可执行（baka / knowthelist 先例）。
"""
import os
import re
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get, save)
from conan.tools.layout import basic_layout


class RobocutConan(ConanFile):
    name = "robocut"
    version = "1.0.11"
    description = ("robocut — SVG 绘图仪/刻字机（Craft Robo / Silhouette）控制程序 "
                   "(Qt5 Widgets GUI + libusb)")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/Timmmm/robocut"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 带 Widgets 的 qt5-qtbase 是 5.15.2.2（5.15.2 为 -no-widgets 构建）；
        # qt5-qtsvg/5.15.2.1 精确声明 qt5-qtbase/5.15.2 → override 统一。
        self.requires("qt5-qtbase/5.15.2.2", override=True)
        self.requires("qt5-qtsvg/5.15.2.1")
        self.requires("libusb/1.0.29")

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os 判断必须 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"robocut only supports Linux and OHOS, got {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ qmake

    @staticmethod
    def _rewrite_build_paths(path, pkg_root):
        """把 .pri 里残留的 conan 构建目录绝对路径改写为 package 目录。"""
        with open(path, "r", encoding="utf-8") as fh:
            content = fh.read()
        fixed = re.sub(r"(/[^\s]*?conan2/p/b/[^/\s]+/b)", pkg_root, content)
        if fixed != content:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(fixed)
        return fixed != content

    def _relocated_qmake(self):
        """构造可重定位的 qmake 视图（qsoas 3.3 先例；另注入 qt5-qtsvg 模块）。"""
        qtbase = self.dependencies["qt5-qtbase"].package_folder
        svg = self.dependencies["qt5-qtsvg"].package_folder
        if not qtbase or not svg:
            raise ConanInvalidConfiguration("qt5-qtbase / qt5-qtsvg package_folder missing")

        root = os.path.join(self.build_folder, "qt-qmake")
        if os.path.isdir(root):
            shutil.rmtree(root)
        mkspecs = os.path.join(root, "mkspecs")
        shutil.copytree(os.path.join(qtbase, "mkspecs"), mkspecs)
        modules = os.path.join(mkspecs, "modules")
        os.makedirs(modules, exist_ok=True)

        # 1) qtbase：用 modules-inst 覆盖 modules 转发件（转发件 include 指向
        #    已删除的构建目录 → 模块变量永不定义 → "Unknown module(s)"）
        inst = os.path.join(qtbase, "mkspecs", "modules-inst")
        qtbase_installed = 0
        if os.path.isdir(inst):
            for name in os.listdir(inst):
                if name.endswith(".pri"):
                    shutil.copy2(os.path.join(inst, name), os.path.join(modules, name))
                    qtbase_installed += 1
        if qtbase_installed == 0:
            raise ConanInvalidConfiguration(
                "qt5-qtbase package has no mkspecs/modules-inst/*.pri")

        # 2) qtsvg：注入 svg 模块；$$QT_MODULE_*_BASE 由 qt_config.prf 统一填
        #    qtbase 路径，这里固化为 qtsvg 包的 lib/include（否则 qt.prf 生成
        #    指向 qtbase 的 libQt5Svg.so 绝对路径，链接必失败）
        svg_inst = os.path.join(svg, "mkspecs", "modules-inst")
        svg_names = set()
        svg_installed = 0
        if os.path.isdir(svg_inst):
            for name in os.listdir(svg_inst):
                if not name.endswith(".pri"):
                    continue
                with open(os.path.join(svg_inst, name), "r", encoding="utf-8") as fh:
                    content = fh.read()
                for token, value in (
                    ("$$QT_MODULE_LIB_BASE", os.path.join(svg, "lib")),
                    ("$$QT_MODULE_HOST_LIB_BASE", os.path.join(svg, "lib")),
                    ("$$QT_MODULE_INCLUDE_BASE", os.path.join(svg, "include")),
                    ("$$QT_MODULE_BIN_BASE", os.path.join(svg, "bin")),
                ):
                    content = content.replace(token, value)
                with open(os.path.join(modules, name), "w", encoding="utf-8") as fh:
                    fh.write(content)
                svg_names.add(name)
                svg_installed += 1
        if svg_installed == 0:
            raise ConanInvalidConfiguration(
                "qt5-qtsvg package has no mkspecs/modules-inst/*.pri")
        self.output.info(
            "qmake modules: qtbase=%d, qtsvg=%d (svg: %s)"
            % (qtbase_installed, svg_installed, ",".join(sorted(svg_names))))

        # 3) 剩余 .pri 的构建目录绝对路径按来源包改写
        rewritten = 0
        for dirpath, _, names in os.walk(mkspecs):
            for name in names:
                if not name.endswith(".pri"):
                    continue
                target = svg if name in svg_names else qtbase
                if self._rewrite_build_paths(os.path.join(dirpath, name), target):
                    rewritten += 1
        self.output.info(f"qmake modules: {rewritten} .pri build-path rewrites")

        # 4) 拷贝 qmake + 写指向 package 的 qt.conf（包内自带的那份 DevicePaths/
        #    Paths/HostPrefix 指向已消失的构建目录）
        bindir = os.path.join(root, "bin")
        os.makedirs(bindir, exist_ok=True)
        qmake = os.path.join(bindir, "qmake")
        packaged_qmake = os.path.join(qtbase, "bin", "qmake")
        if not os.path.isfile(packaged_qmake):
            raise ConanInvalidConfiguration(
                f"qt5-qtbase package does not provide qmake: {packaged_qmake}")
        shutil.copy2(packaged_qmake, qmake)
        os.chmod(qmake, stat.S_IMODE(os.stat(qmake).st_mode) | 0o755)
        save(self, os.path.join(bindir, "qt.conf"),
             "[EffectivePaths]\nPrefix=..\n"
             "[DevicePaths]\nPrefix={0}\n"
             "[Paths]\nPrefix={0}\nHostPrefix={0}\n"
             "Sysroot=\nSysrootifyPrefix=false\n"
             "TargetSpec=linux-clang\nHostSpec=linux-clang\n".format(qtbase))
        return root, qmake, modules

    def _build_env(self, qt_root, qt_modules):
        env = Environment()
        qtbase = self.dependencies["qt5-qtbase"].package_folder
        svg = self.dependencies["qt5-qtsvg"].package_folder
        libusb = self.dependencies["libusb"].package_folder

        env.prepend_path("PATH", os.path.join(qtbase, "bin"))
        env.prepend_path("PATH", "/data/service/hnp/bin")
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(qtbase, "lib"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(svg, "lib"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(libusb, "lib"))
        # 模块 .pri 的搜索路径（qt_config.prf 会把它排在 $$[QMAKE_MKSPECS]/modules
        # 之后加载，从而覆盖包内那份损坏的转发件）
        env.define("QMAKEMODULES", qt_modules)
        # 上游写 <libusb-1.0/libusb.h>：libusb 包 includedirs=include/libusb-1.0
        # 只覆盖 <libusb.h> 形态 → 这里补 <pkg>/include（CPATH 必须冒号拼接）
        env.define("CPATH", os.path.join(libusb, "include"))
        env.define("LIBRARY_PATH", os.path.join(libusb, "lib"))
        env.define("CC", "/data/service/hnp/bin/clang")
        env.define("CXX", "/data/service/hnp/bin/clang++")
        return env

    def build(self):
        apply_conandata_patches(self)

        pro = os.path.join(self.source_folder, "Robocut.pro")
        if not os.path.isfile(pro):
            raise ConanInvalidConfiguration(f"Robocut.pro not found: {pro}")

        qt_root, qmake, qt_modules = self._relocated_qmake()
        env = self._build_env(qt_root, qt_modules)
        with env.vars(self).apply():
            # 内联 PATH 前缀双保险（部分 CI worker 上 Environment 注入不可靠，
            # knowthelist 2.3.1 先例）
            prefix = (f'PATH="{os.path.join(qt_root, "bin")}:'
                      f'/data/service/hnp/bin:$PATH" '
                      f'QMAKEMODULES="{qt_modules}" ')
            self.run(prefix + f'"{qmake}" Robocut.pro -spec linux-clang QMAKE_STRIP=',
                     cwd=self.source_folder)
            makefile = os.path.join(self.source_folder, "Makefile")
            with open(makefile, "r", encoding="utf-8") as fh:
                generated = fh.read()
            # 反静默守卫（qsoas 3.3 先例）：生成的 Makefile 不得引用 Qt 的历史
            # 构建缓存目录（形如 .../conan2/p/b/qt5-qXXXX/b/...，早已不存在）
            stale = re.search(r"conan2/p/b/qt[^\s]*?/b/", generated)
            if stale:
                raise ConanInvalidConfiguration(
                    "qmake generated a command using Qt's historical build cache: "
                    + stale.group(0))
            self.run(prefix + "make -j2 QMAKE_STRIP=", cwd=self.source_folder)

    def package(self):
        # 上游 INSTALLS += target icon；target.path=/usr/bin、
        # icon.path=/usr/share/pixmaps → make install INSTALL_ROOT=<pkg>
        # 落 <pkg>/usr/...，再归一化到 <pkg>/{bin,share}（knowthelist 先例）
        qt_root, qmake, qt_modules = self._relocated_qmake()
        env = self._build_env(qt_root, qt_modules)
        with env.vars(self).apply():
            prefix = (f'PATH="{os.path.join(qt_root, "bin")}:'
                      f'/data/service/hnp/bin:$PATH" '
                      f'QMAKEMODULES="{qt_modules}" ')
            self.run(prefix + f'make install INSTALL_ROOT="{self.package_folder}" '
                              'STRIP=true', cwd=self.source_folder)

        usr = os.path.join(self.package_folder, "usr")
        if os.path.isdir(usr):
            for sub in ("bin", "share", "lib", "etc"):
                sub_src = os.path.join(usr, sub)
                if not os.path.isdir(sub_src):
                    continue
                sub_dst = os.path.join(self.package_folder, sub)
                os.makedirs(sub_dst, exist_ok=True)
                for entry in os.listdir(sub_src):
                    shutil.move(os.path.join(sub_src, entry),
                                os.path.join(sub_dst, entry))
            shutil.rmtree(usr, ignore_errors=True)

        # 兜底：make install 未落 target 时直接从构建树复制（并出声）
        binary = os.path.join(self.package_folder, "bin", "robocut")
        if not os.path.isfile(binary):
            built = os.path.join(self.source_folder, "robocut")
            if os.path.isfile(built):
                self.output.warning(
                    "make install did not place bin/robocut; copying from build tree")
                copy(self, "robocut", src=self.source_folder,
                     dst=os.path.join(self.package_folder, "bin"))
            else:
                raise ConanInvalidConfiguration(
                    "robocut binary not produced by the build")
        os.chmod(binary, 0o755)

    def package_info(self):
        # 应用包（TEMPLATE=app），无库文件供下游链接
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
