#!/usr/bin/env python3
"""Conan recipe — mystiq 20.03.23 (Qt5 + qmake 音视频转码 GUI，HarmonyOS PC aarch64).

上游: https://github.com/swl-x/MystiQ (tag v20.03.23)
构建: qmake + make（mystiq.pro），需 Qt5 模块化栈：
      qt5-qtbase/5.15.2.2 + qt5-qtdeclarative/5.15.2 + qt5-qtmultimedia/5.15.2

鸿蒙适配要点:
  1. Qt5 三个 conan 包各自是独立前缀，qmake 只认单一 QT_INSTALL_* 前缀。
     本配方在 build_folder 内构建合并的 qt5-root（bin/lib/include/mkspecs/
     plugins/qml），并把 .pri/.prl 中记录的 conan 构建目录绝对路径改写为
     各依赖包的 package_folder（构建目录已随 conan 清理消失，不改写则
     qmake 报 Unknown module(s) / 找不到 libQt5Core.so）。
  2. R49: 合并树建在 build_folder（私有一致前缀），不写 /usr/local 等共享目录。
  3. R33: 不读裸 shell 环境变量，qmake/make 全部用绝对路径调用。
  4. 无 X11/Wayland：本包按 headless QPA（offscreen/minimal）验证；ffmpeg/ffprobe
     是运行期外部 CLI，由下游部署注入，不在本包内链接。
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

# conan 构建目录形如 .../.conan2/p/b/qt5-qXXXX/b 或 .../.cache/conan2/p/b/qt5-qXXXX/b
_BUILD_DIR_RE = re.compile(r"/[^\s\"']*?conan2/p/b/[^/\s\"']+/b")


class MystiqConan(ConanFile):
    name = "mystiq"
    version = "20.03.23"
    description = ("MystiQ — a Qt5 GUI frontend for ffmpeg (audio/video converter), "
                   "HarmonyOS PC aarch64 adaptation")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/swl-x/MystiQ"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # 鸿蒙特有测试随配方分发（tests/testohosplatform 目录在上游源码中不存在，
        # 用补丁无法创建目录，故作为 recipe 附加源码在 build() 中落地）
        copy(self, "*", src=os.path.join(self.recipe_folder, "ohos-tests"),
             dst=os.path.join(self.export_sources_folder, "ohos-tests"))
        export_conandata_patches(self)

    def requirements(self):
        # Qt5 模块化栈：qt5-qtbase/5.15.2 为 -no-widgets/-no-dbus headless 构建，
        # mystiq 需要 Widgets 与 Qt5DBus，必须使用 5.15.2.2。
        self.requires("qt5-qtbase/5.15.2.2")
        self.requires("qt5-qtdeclarative/5.15.2")
        self.requires("qt5-qtmultimedia/5.15.2")

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os 判断必须 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"mystiq supports Linux and OHOS only, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ─────────────────────────────────────────────────────────────
    # Qt5 合并前缀
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def _rewrite_text_file(path, mapping):
        """把文本文件里的 conan 构建目录路径替换为对应 package_folder。"""
        try:
            with open(path, "r", encoding="utf-8", errors="surrogateescape") as fh:
                original = fh.read()
        except OSError:
            return
        fixed = original
        for build_dir, pkg_root in mapping.items():
            fixed = fixed.replace(build_dir, pkg_root)
        fixed = _BUILD_DIR_RE.sub(lambda m: mapping.get(m.group(0), m.group(0)), fixed)
        if fixed != original:
            with open(path, "w", encoding="utf-8", errors="surrogateescape") as fh:
                fh.write(fixed)

    def _discover_build_dirs(self, pkg_root):
        """从包内 mkspecs 的 .pri 里发现该包被硬编码的构建目录路径。"""
        dirs = set()
        mkspecs = os.path.join(pkg_root, "mkspecs")
        for sub in ("modules", "modules-inst"):
            d = os.path.join(mkspecs, sub)
            if not os.path.isdir(d):
                continue
            for name in os.listdir(d):
                if not name.endswith(".pri"):
                    continue
                try:
                    with open(os.path.join(d, name), "r",
                              encoding="utf-8", errors="surrogateescape") as fh:
                        content = fh.read()
                except OSError:
                    continue
                dirs.update(_BUILD_DIR_RE.findall(content))
        return dirs

    def _prepare_qt5_root(self):
        deps = {
            "qt5-qtbase": self.dependencies["qt5-qtbase"],
            "qt5-qtdeclarative": self.dependencies["qt5-qtdeclarative"],
            "qt5-qtmultimedia": self.dependencies["qt5-qtmultimedia"],
        }
        for name, dep in deps.items():
            if dep.package_folder is None:
                raise ConanInvalidConfiguration(f"{name} package_folder is None")

        root = os.path.join(self.build_folder, "qt5-root")
        if os.path.isdir(root):
            shutil.rmtree(root)
        for sub in ("bin", "lib", "include", "plugins", "qml", "translations",
                    os.path.join("mkspecs", "modules"),
                    os.path.join("mkspecs", "modules-inst")):
            os.makedirs(os.path.join(root, sub), exist_ok=True)

        # 每个包的构建目录 -> package_folder 映射
        mapping = {}
        for name, dep in deps.items():
            pkg_root = dep.package_folder
            for build_dir in self._discover_build_dirs(pkg_root):
                mapping[build_dir] = pkg_root

        # bin：复制（qt.conf 依赖可执行文件的真实路径，符号链接会被解析回原包）
        qb_bin = os.path.join(deps["qt5-qtbase"].package_folder, "bin")
        for name in sorted(os.listdir(qb_bin)):
            src = os.path.join(qb_bin, name)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(root, "bin", name))

        # include / lib / plugins / qml / translations：符号链接合并
        for name, dep in deps.items():
            pkg_root = dep.package_folder
            for sub, target in (("include", "include"), ("plugins", "plugins")):
                src_dir = os.path.join(pkg_root, sub)
                if not os.path.isdir(src_dir):
                    continue
                for entry in sorted(os.listdir(src_dir)):
                    dst = os.path.join(root, target, entry)
                    if os.path.exists(dst):
                        continue
                    src = os.path.join(src_dir, entry)
                    if target == "plugins" and os.path.isdir(src):
                        os.makedirs(dst, exist_ok=True)
                        for plugin in sorted(os.listdir(src)):
                            pdst = os.path.join(dst, plugin)
                            if not os.path.exists(pdst):
                                os.symlink(os.path.join(src, plugin), pdst)
                    else:
                        os.symlink(src, dst)

            lib_dir = os.path.join(pkg_root, "lib")
            if os.path.isdir(lib_dir):
                for entry in sorted(os.listdir(lib_dir)):
                    if entry.endswith(".prl"):
                        continue  # .prl 单独重写为真实文件
                    dst = os.path.join(root, "lib", entry)
                    if os.path.exists(dst):
                        continue
                    os.symlink(os.path.join(lib_dir, entry), dst)

        # mkspecs：复制 qtbase 全量，再叠加 declarative/multimedia 的 .pri（重写路径）
        shutil.copytree(os.path.join(deps["qt5-qtbase"].package_folder, "mkspecs"),
                        os.path.join(root, "mkspecs"), dirs_exist_ok=True)
        for sub in ("modules", "modules-inst"):
            dst_dir = os.path.join(root, "mkspecs", sub)
            for name in sorted(os.listdir(dst_dir)):
                path = os.path.join(dst_dir, name)
                if os.path.isfile(path):
                    self._rewrite_text_file(path, mapping)
        # 依赖包的 .pri 叠进合并树（qtbase 已复制，跳过重复）
        for dep_name in ("qt5-qtdeclarative", "qt5-qtmultimedia"):
            pkg_root = deps[dep_name].package_folder
            for sub in ("modules", "modules-inst"):
                src_dir = os.path.join(pkg_root, "mkspecs", sub)
                if not os.path.isdir(src_dir):
                    continue
                for name in sorted(os.listdir(src_dir)):
                    if not name.endswith(".pri"):
                        continue
                    dst = os.path.join(root, "mkspecs", sub, name)
                    shutil.copy2(os.path.join(src_dir, name), dst)
                    self._rewrite_text_file(dst, mapping)
        # .pri 里的 include(<pkg>/mkspecs/modules-inst/...) 统一指向合并树副本
        for sub in ("modules", "modules-inst"):
            dst_dir = os.path.join(root, "mkspecs", sub)
            for name in sorted(os.listdir(dst_dir)):
                path = os.path.join(dst_dir, name)
                if not os.path.isfile(path):
                    continue
                try:
                    with open(path, "r", encoding="utf-8", errors="surrogateescape") as fh:
                        content = fh.read()
                except OSError:
                    continue
                fixed = content
                for dep in deps.values():
                    fixed = fixed.replace(
                        os.path.join(dep.package_folder, "mkspecs", "modules-inst"),
                        os.path.join(root, "mkspecs", "modules-inst"))
                if fixed != content:
                    with open(path, "w", encoding="utf-8", errors="surrogateescape") as fh:
                        fh.write(fixed)

        # .prl：生成真实文件（绝不能 > 直写符号链接，会跟随链接清空依赖包源文件）
        for name, dep in deps.items():
            lib_dir = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(lib_dir):
                continue
            for entry in sorted(os.listdir(lib_dir)):
                if not entry.endswith(".prl"):
                    continue
                src = os.path.join(lib_dir, entry)
                tmp = os.path.join(root, "lib", ".tmp-" + entry)
                with open(src, "r", encoding="utf-8", errors="surrogateescape") as fh:
                    content = fh.read()
                for build_dir, pkg_root in mapping.items():
                    content = content.replace(build_dir, pkg_root)
                content = _BUILD_DIR_RE.sub(
                    lambda m: mapping.get(m.group(0), m.group(0)), content)
                with open(tmp, "w", encoding="utf-8", errors="surrogateescape") as fh:
                    fh.write(content)
                dst = os.path.join(root, "lib", entry)
                if os.path.islink(dst):
                    os.unlink(dst)
                os.replace(tmp, dst)

        # qml 模块（declarative）
        qd_qml = os.path.join(deps["qt5-qtdeclarative"].package_folder, "qml")
        if os.path.isdir(qd_qml):
            for entry in sorted(os.listdir(qd_qml)):
                dst = os.path.join(root, "qml", entry)
                if not os.path.exists(dst):
                    os.symlink(os.path.join(qd_qml, entry), dst)

        # qt.conf：前缀指向合并树（qmake 依赖自身可执行文件路径定位 qt.conf）
        qt_conf = os.path.join(root, "bin", "qt.conf")
        if os.path.islink(qt_conf) or os.path.exists(qt_conf):
            os.unlink(qt_conf)
        with open(qt_conf, "w", encoding="utf-8") as fh:
            fh.write("[EffectivePaths]\nPrefix=..\n\n"
                     "[Paths]\n"
                     f"Prefix={root}\n"
                     f"HostPrefix={root}\n"
                     "Sysroot=\n"
                     "SysrootifyPrefix=false\n"
                     "TargetSpec=linux-clang\n"
                     "HostSpec=linux-clang\n")

        self.output.info(f"Qt5 merged prefix: {root}")
        return root

    # ─────────────────────────────────────────────────────────────

    def build(self):
        if self.conan_data.get("patches"):
            apply_conandata_patches(self)

        # 落地鸿蒙特有测试（tests/testohosplatform）
        test_dst = os.path.join(self.source_folder, "tests", "testohosplatform")
        os.makedirs(test_dst, exist_ok=True)
        copy(self, "*", src=os.path.join(self.export_sources_folder, "ohos-tests"),
             dst=test_dst)

        root = self._prepare_qt5_root()
        qmake = os.path.join(root, "bin", "qmake")
        if not os.path.isfile(qmake):
            raise ConanInvalidConfiguration(f"qmake not found in merged prefix: {qmake}")

        env = Environment()
        env.prepend_path("PATH", os.path.join(root, "bin"))
        env.prepend_path("PATH", "/data/service/hnp/bin")
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(root, "lib"))
        env.define("QMAKEMODULES", os.path.join(root, "mkspecs", "modules"))

        with env.vars(self).apply():
            self.run(f'"{qmake}" mystiq.pro -spec linux-clang', cwd=self.source_folder)
            # QMAKE_STRIP 置空：OHOS 加载器拒绝 strip 后的 ELF（历史踩坑）
            self.run('make -j2 QMAKE_STRIP=""', cwd=self.source_folder)

    def package(self):
        exe = os.path.join(self.source_folder, "mystiq")
        if not os.path.isfile(exe):
            raise ConanInvalidConfiguration(f"build artifact missing: {exe}")
        copy(self, "mystiq", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "mystiq.desktop", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "applications"))
        copy(self, "mystiq.svg", src=os.path.join(self.source_folder, "icons"),
             dst=os.path.join(self.package_folder, "share", "icons", "hicolor",
                              "scalable", "apps"))
        copy(self, "mystiq.appdata.xml", src=os.path.join(self.source_folder, "metainfo"),
             dst=os.path.join(self.package_folder, "share", "metainfo"))
        copy(self, "mystiq.1.gz", src=os.path.join(self.source_folder, "man"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        # 运行期数据（DATA_PATH 为空时 mystiq 使用可执行文件同级作为 datapath）
        copy(self, "presets.xml", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "constants.xml", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
