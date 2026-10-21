#!/usr/bin/env python3
"""Conan recipe — xdrawchem 1.11.1 (XDrawChem, Qt5 二维分子结构绘制/分析程序, qmake 工程).

上游: https://gitlab.com/yamanq/xdrawchem (tag v1.11.1)
构建: qmake + make（上游 xdrawchem.pro，in-source，产物 bin/xdrawchem）

依赖链（W0 依赖发布检查确认均已发布）:
  QT += core gui widgets network xml printsupport  -> qt5-qtbase/5.15.2.2
  QT += svg                                        -> qt5-qtsvg/5.15.2
  PKGCONFIG += openbabel-3                         -> openbabel/3.2.1

OHOS 适配要点:
  1. qt5-qtsvg/5.15.2 精确引用 qt5-qtbase/5.15.2（该版本为 -no-widgets 构建，
     不含 Qt5Widgets），xdrawchem 需要 Widgets，故统一 override 到 5.15.2.2。
  2. qt5-qtbase / qt5-qtsvg 包内 mkspecs/modules/*.pri 与 bin/qt.conf 记录的
     是**构建期**的 conan 私有前缀（`.../p/b/<hash>/b`，随构建目录清理消失），
     qmake 直接引用会 `Project ERROR: Unknown module(s) in QT: ...`，并让
     rcc/moc/uic 解析到失效路径。这里把 .pri 复制到构建目录、逐处改写为真实
     package 目录并用 QMAKEMODULES 暴露，同时用修正后的 qt.conf（-qtconf）
     重定位 Prefix，并显式钉住 QMAKE_RCC/QMAKE_MOC/QMAKE_UIC（qconf 2.5 先例）。
  3. openbabel 包内 lib/pkgconfig/openbabel-3.pc 的 prefix 同样指向已消失的
     构建目录，改用 Conan PkgConfigDeps 重新生成干净的 openbabel-3.pc。
  4. 上游 install_target 规则会 strip 安装后的二进制，而 OHOS 加载器拒绝 stripped
     ELF（execve 直接 EPERM）：须在 qmake 命令行传 QMAKE_STRIP=true，使生成的
     Makefile 里 STRIP=true（环境变量 QMAKE_STRIP 与 make QMAKE_STRIP= 均无效，
     Makefile 的变量名是 STRIP）。
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout

# 构建期 conan 私有前缀（`.../p/b/<hash>/b` 或 `/p`）→ 真实 package 目录。
# 必须以 `/` 起始锚定路径开头，否则 `include(/…/b/…)` 的前缀会被连带吃掉。
_STALE_PREFIX_RE = re.compile(
    r"/[^\s\"'()]*?/p/b/[^/\s\"'()]+/[bp](?=/|$|\s|\"|')"
)


class XdrawchemConan(ConanFile):
    name = "xdrawchem"
    version = "1.11.1"
    description = "XDrawChem — 2D molecule drawing and analysis program (Qt5 + Open Babel)"
    license = "GPL-3.0-or-later"
    homepage = "https://gitlab.com/yamanq/xdrawchem"
    url = "https://gitlab.com/yamanq/xdrawchem"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # qt5-qtbase/5.15.2.2 才带 Qt5Widgets；qt5-qtsvg/5.15.2 的 recipe 精确
        # 引用 qt5-qtbase/5.15.2，用 override 统一（5.15.2.x 补丁版本 API 兼容，
        # 二进制无需重建）。
        self.requires("qt5-qtbase/5.15.2.2", override=True)
        self.requires("qt5-qtsvg/5.15.2")
        self.requires("openbabel/3.2.1")

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os 判断必须 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xdrawchem only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # openbabel 包内的 openbabel-3.pc 记录的是构建期目录（已消失），
        # 由 PkgConfigDeps 重新生成干净的 openbabel-3.pc（含传递依赖 libxml2）。
        deps = PkgConfigDeps(self)
        deps.set_property("openbabel", "pkg_config_name", "openbabel-3")
        deps.generate()

    # ── Qt5 qmake 环境修复 ────────────────────────────────────────────────

    def _setup_qmake_modules(self, build_env):
        """修复 qt5-qtbase/qt5-qtsvg 模块 .pri 的构建期绝对路径。

        包内 `mkspecs/modules/qt_lib_*.pri` 与 `modules-inst/*.pri` 记录的是
        构建期 conan 私有前缀（已随构建目录清理消失）：qmake 解析 `QT += core
        gui widgets …` 时报 `Unknown module(s) in QT`。复制到构建目录并把路径
        改写为真实 package 目录后，经 QMAKEMODULES 暴露给 qmake。
        """
        modules_root = os.path.join(self.build_folder, "qmake-modules")
        modules_dir = os.path.join(modules_root, "modules")
        modules_inst_dir = os.path.join(modules_root, "modules-inst")
        for directory in (modules_dir, modules_inst_dir):
            os.makedirs(directory, exist_ok=True)

        for dep_name in ("qt5-qtbase", "qt5-qtsvg"):
            dep = self.dependencies[dep_name]
            if dep.package_folder is None:
                continue
            pkg_root = dep.package_folder
            for sub, target in (
                ("mkspecs/modules", modules_dir),
                ("mkspecs/modules-inst", modules_inst_dir),
            ):
                src = os.path.join(pkg_root, sub)
                if not os.path.isdir(src):
                    continue
                for pri in os.listdir(src):
                    if pri.endswith(".pri"):
                        shutil.copy2(os.path.join(src, pri), os.path.join(target, pri))
            for directory in (modules_dir, modules_inst_dir):
                for pri in os.listdir(directory):
                    if not pri.endswith(".pri"):
                        continue
                    path = os.path.join(directory, pri)
                    with open(path, "r", encoding="utf-8", errors="replace") as handle:
                        content = handle.read()
                    fixed = _STALE_PREFIX_RE.sub(pkg_root, content)
                    if fixed != content:
                        with open(path, "w", encoding="utf-8") as handle:
                            handle.write(fixed)
        build_env.define("QMAKEMODULES", modules_dir)

    def _write_qt_conf(self, qtbase_folder):
        """生成指向真实 package 目录的 qt.conf 并用 qmake -qtconf 加载。

        qt5-qtbase 包内 bin/qt.conf 的 [Paths] Prefix 记录的是构建期目录，
        rcc/moc/uic 与产物 RUNPATH 都会解析到失效路径。覆写 Prefix/HostPrefix
        即同时修好两者（注意不能带 [EffectivePaths] Prefix=..，否则 -qtconf
        找不到 mkspec）。
        """
        qt_conf = os.path.join(self.build_folder, "qt.conf")
        with open(qt_conf, "w", encoding="utf-8") as handle:
            handle.write(
                "[Paths]\n"
                f"Prefix={qtbase_folder}\n"
                f"HostPrefix={qtbase_folder}\n"
                "Sysroot=\n"
            )
        return qt_conf

    def build(self):
        # conan 2.29 无 conan.tools.qmake 模块，参照 archives/q/qconf/2.5 与
        # archives/b/baka/2.0.4 先例，用 self.run 直接调用 qmake + make。
        qtbase = self.dependencies["qt5-qtbase"]
        qmake = os.path.join(qtbase.package_folder, "bin", "qmake")
        if not os.path.isfile(qmake):
            raise ConanException(
                f"qt5-qtbase 包内未找到 qmake（包不完整）: {qmake}"
            )

        qt_conf = self._write_qt_conf(qtbase.package_folder)
        qt_bin = os.path.join(qtbase.package_folder, "bin")
        tool_overrides = " ".join(
            f'"{var}={os.path.join(qt_bin, tool)}"'
            for var, tool in (("QMAKE_RCC", "rcc"), ("QMAKE_MOC", "moc"), ("QMAKE_UIC", "uic"))
        )

        build_env = Environment()
        # qmake/moc/uic/rcc 是链接 Qt 库的可执行文件，运行期需要 Qt 库目录
        build_env.prepend_path("LD_LIBRARY_PATH", os.path.join(qtbase.package_folder, "lib"))
        # PkgConfigDeps 把 *.pc 生成到 generators 目录，但不会注入
        # PKG_CONFIG_PATH；qmake 的 PKGCONFIG += openbabel-3 需要它。
        pkg_paths = [self.generators_folder]
        existing_pkg = os.environ.get("PKG_CONFIG_PATH")
        if existing_pkg:
            pkg_paths.append(existing_pkg)
        build_env.define("PKG_CONFIG_PATH", os.pathsep.join(pkg_paths))
        self._setup_qmake_modules(build_env)

        with build_env.vars(self).apply():
            # in-source build（上游 .pro 仅支持 in-source）；-spec linux-clang
            # 匹配 OHOS clang 工具链；CONFIG 按 conan build_type 显式指定
            # （补丁已移除上游硬编码的 `CONFIG += debug`）；
            # PREFIX 指向包目录，使上游 INSTALLS 规则直接安装到位。
            # QMAKE_STRIP=true：install_target 规则会执行 `-$(STRIP) <安装后的二进制>`，
            # 而 OHOS 加载器拒绝 stripped ELF（实测 strip 后 execve 直接
            # "Operation not permitted"），故必须在 **qmake 期**把 Makefile 的
            # STRIP 变量改写为 true（环境变量 QMAKE_STRIP 或 make 命令行
            # QMAKE_STRIP= 都无效：Makefile 里的变量名是 STRIP）。
            build_config = (
                "CONFIG+=debug" if str(self.settings.build_type) == "Debug" else "CONFIG+=release"
            )
            self.run(
                f'cd "{self.source_folder}" && '
                f'"{qmake}" -qtconf "{qt_conf}" xdrawchem.pro -spec linux-clang '
                f"{build_config} "
                f'PREFIX="{self.package_folder}" QMAKE_STRIP=true {tool_overrides}'
            )
            # 本环境 make -j>1 触发 jobserver mkfifo（HMDFS 不允许 mkfifo），用 -j1
            self.run(f'cd "{self.source_folder}" && make -j1')

    def package(self):
        # 上游 INSTALLS 规则（target/ringdir/doc）以 PREFIX=包目录安装：
        # bin/xdrawchem + share/xdrawchem/{ring 内容, doc/}
        self.run(f'cd "{self.source_folder}" && make install')
        binary = os.path.join(self.package_folder, "bin", "xdrawchem")
        if not os.path.isfile(binary):
            raise ConanException(
                f"未找到打包产物 {binary}（上游 qmake 安装规则未生效）"
            )

    def package_info(self):
        # 二进制应用（TEMPLATE=app），无供下游链接的库
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []  # 应用无导出库，显式置空自证非遗漏
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
