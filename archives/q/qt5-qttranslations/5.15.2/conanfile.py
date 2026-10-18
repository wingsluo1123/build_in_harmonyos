#!/usr/bin/env python3
"""Conan recipe for qt5-qttranslations 5.15.2 on OpenHarmony PC.

Qt5 翻译资源包：把上游 translations/*.ts 编译为 translations/*.qm，落位到包前缀的
translations/ 下（Qt5 的 QT_INSTALL_TRANSLATIONS 约定）。本件是**纯资源包**——
没有 C/C++ 编译、没有可执行文件、没有链接库，因此 package_type="unknown"，
构建阶段只做资源转换与打包。

上游 5.15.2 是 qmake 工程（qttranslations.pro -> translations/translations.pro，
TEMPLATE=aux）：其 `updateqm` 编译器用 Qt Linguist 的 lrelease 把每条
TRANSLATIONS(.ts) 转成 .qm，并额外生成 <module>_en.ts（空 source 语言占位）
一并安装。本配方忠实复刻该语义：逐 .ts 调 lrelease 生成 .qm，并补齐 _en 占位
（共 266 源 .ts + 17 个 _en.ts = 283 个 .qm）。

lrelease 来源（关键工具链约束，勿改）：
  制品仓没有任何 Qt5 的 qttools 包（qt5-qttools/5.15.2、qttools/5.15.2 均 404），
  而 qt5-qtbase 只含 Qt5 基础模块（不含 Qt Linguist）。故按既有结论
  （knowledge/drafts/mlite-0.5.5-qt5-qttools-missing-lrelease.kv；mlite 0.5.5
  先例）使用已发布的 Qt6 qttools/6.11.1.1 的 lrelease 作为构建工具：Qt6
  lrelease 读 Qt5 的 .ts、写标准 .qm；且实测 Qt5.15 的 QTranslator 能正常加载
  其产物（test_package 用 qt5-qtbase 的 QTranslator 实测验证，非纸面断言）。
"""
import glob
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# 上游 translations.pro 的 TS_MODULES（write_file(..._en.ts) 生成的空翻译模块）
_EN_MODULES = (
    "qtbase",
    "qtdeclarative",
    "qtquickcontrols",
    "qtquickcontrols2",
    "qtmultimedia",
    "qtscript",
    "qtxmlpatterns",
    "qtconnectivity",
    "qtlocation",
    "qtwebsockets",
    "qtserialport",
    "qtwebengine",
    "designer",
    "linguist",
    "assistant",
    "qt_help",
)
# 上游 updateqm 之外的 qt_en.ts（source 语言占位）
_QT_EN = "qt"
_EMPTY_TS = "<TS></TS>"


class Qt5QttranslationsConan(ConanFile):
    name = "qt5-qttranslations"
    version = "5.15.2"
    description = "Qt5 translations resources (translations/*.qm) for OpenHarmony"
    license = "LGPL-3.0"
    homepage = "https://www.qt.io/"

    # L0p：OHOS profile 需要 os/compiler/build_type/arch 四项
    settings = "os", "compiler", "build_type", "arch"
    # 纯翻译资源包（产物仅为 translations/*.qm），无 lib/bin → unknown
    package_type = "unknown"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} only supports Linux and OHOS, got {self.settings.os}"
            )

    def requirements(self):
        # Qt5 基座：本资源包服务的 Qt5 模块族；test_package 用其 QTranslator
        # 真实加载产出的 .qm（消费者视角验证）。
        self.requires("qt5-qtbase/5.15.2.2")
        # lrelease 构建工具：制品仓无 Qt5 qttools，按 mlite 0.5.5 结论用 Qt6 qttools。
        self.requires("qttools/6.11.1.1")

    def source(self):
        source_data = self.conan_data["sources"][self.version]
        urls = source_data["url"]
        if isinstance(urls, str):
            urls = [urls]
        for url in urls:
            try:
                get(
                    self,
                    url=url,
                    sha256=source_data.get("sha256", ""),
                    strip_root=True,
                )
                return
            except ConanException as error:  # noqa: BLE001
                self.output.warning(f"Failed to download source from {url}: {error}")
        raise ConanInvalidConfiguration("Unable to download source from all mirrors")

    # ── lrelease（来自 Qt6 qttools）运行环境 ──────────────────────────────

    def _lrelease_path(self):
        qttools = self.dependencies["qttools"]
        lrelease = os.path.join(qttools.package_folder, "bin", "lrelease")
        if not os.path.isfile(lrelease):
            raise ConanException("qttools/6.11.1.1 does not provide bin/lrelease")
        return lrelease

    def _dep_lib_dir(self, name):
        try:
            dep = self.dependencies[name]
        except Exception:  # noqa: BLE001 - 依赖名可能不在图中
            return None
        lib_dir = os.path.join(dep.package_folder, "lib")
        return lib_dir if os.path.isdir(lib_dir) else None

    def _cxx_runtime_lib_dirs(self):
        """从工具链 clang++ 路径推导 OHOS SDK 的 libc++ 运行库目录
        （lrelease 需 libc++_shared.so；profile [buildenv] 通常已提供，这里
        作为不依赖 profile 的兜底，且不硬编码 SDK 版本号）。"""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = compilers.get("cpp") or compilers.get("cxx")
        if not cxx:
            return []
        real = os.path.realpath(shlex.split(cxx)[0])
        base = os.path.dirname(real)
        candidates = (
            os.path.join(base, "..", "lib", "aarch64-linux-ohos"),
            os.path.join(base, "..", "lib"),
        )
        return [os.path.abspath(p) for p in candidates if os.path.isdir(p)]

    def _lrelease_environment(self):
        """Qt6 lrelease 动态链接 libQt6Core/Qt6Network（qtbase）与 libQt6Qml
        （qtdeclarative），且无 RUNPATH → 显式拼 LD_LIBRARY_PATH。"""
        env = Environment()
        for name in ("qttools", "qtbase", "qtdeclarative"):
            lib_dir = self._dep_lib_dir(name)
            if lib_dir:
                env.prepend_path("LD_LIBRARY_PATH", lib_dir)
        for lib_dir in self._cxx_runtime_lib_dirs():
            env.prepend_path("LD_LIBRARY_PATH", lib_dir)
        return env

    def _write_empty_ts(self, path):
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(_EMPTY_TS)

    # ── build / package ────────────────────────────────────────────────

    def build(self):
        translations_src = os.path.join(self.source_folder, "translations")
        ts_files = sorted(glob.glob(os.path.join(translations_src, "*.ts")))
        if not ts_files:
            raise ConanException(f"no .ts resources found under {translations_src}")

        out_dir = os.path.join(self.build_folder, "translations")
        os.makedirs(out_dir, exist_ok=True)

        # 复刻上游 translations.pro：为每个模块写一个空的 <module>_en.ts 占位
        for module in _EN_MODULES:
            self._write_empty_ts(os.path.join(out_dir, f"{module}_en.ts"))
        self._write_empty_ts(os.path.join(out_dir, f"{_QT_EN}_en.ts"))

        lrelease = self._lrelease_path()
        env = self._lrelease_environment()
        ts_all = ts_files + sorted(glob.glob(os.path.join(out_dir, "*.ts")))
        generated = 0
        with env.vars(self).apply():
            for ts_file in ts_all:
                base = os.path.splitext(os.path.basename(ts_file))[0]
                qm_file = os.path.join(out_dir, f"{base}.qm")
                self.run(
                    f"{shlex.quote(lrelease)} {shlex.quote(ts_file)} "
                    f"-qm {shlex.quote(qm_file)}"
                )
                if not os.path.isfile(qm_file):
                    raise ConanException(
                        f"lrelease did not produce {qm_file} from {ts_file}"
                    )
                generated += 1
        self.output.info(
            f"qt5-qttranslations: generated {generated} .qm files "
            f"({len(ts_files)} upstream + {len(ts_all) - len(ts_files)} _en placeholders)"
        )

    def package(self):
        out_dir = os.path.join(self.build_folder, "translations")
        copy(
            self,
            "*.qm",
            src=out_dir,
            dst=os.path.join(self.package_folder, "translations"),
        )
        packaged = glob.glob(
            os.path.join(self.package_folder, "translations", "*.qm")
        )
        if not packaged:
            raise ConanException("no .qm file was packaged")
        self.output.info(
            f"qt5-qttranslations: packaged {len(packaged)} .qm files "
            f"under translations/"
        )

    def package_info(self):
        # 纯资源包：无头文件/无库/无可执行文件；翻译资源以 resdirs 暴露
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.resdirs = ["translations"]
        # 消费者运行期翻译目录（Qt5 QT_INSTALL_TRANSLATIONS 等价约定）
        self.runenv_info.define_path(
            "QT_TRANSLATIONS_PATH",
            os.path.join(self.package_folder, "translations"),
        )
