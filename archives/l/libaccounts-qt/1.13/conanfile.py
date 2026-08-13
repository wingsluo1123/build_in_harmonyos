#!/usr/bin/env python3
"""Conan recipe — libaccounts-qt 1.13 (手动 moc + clang++ 构建)

qt5-qtbase/5.15.2 包内 qmake 的 QMAKE_MKSPECS 被编译固化指向构建期 build
目录（消费者环境不存在），导致 `QT += core` 模块发现失败（Unknown module）。
qt.conf Prefix/TargetSpec、QMAKEPATH/QMAKESPEC 环境变量均无法覆盖该固化值。
因此绕过 qmake 模块系统：直接用 qt5-qtbase 包内 moc + clang++ 编译。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps


class LibaccountsQtConan(ConanFile):
    name = "libaccounts-qt"
    version = "1.13"
    description = "Qt-based client library for accessing the online accounts database"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.com/accounts-sso/libaccounts-qt"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R36: qt5-qtbase 5.15.2.1（含 QtXml 模块）/ libaccounts-glib 1.27
        # 注意：qt5-qtbase/5.15.2 以 -no-feature-xml 构建，QtXml 头/库缺失
        # （qtxml-config.h 未生成），而 libaccounts-qt 的 service.h 依赖
        # QDomDocument，必须用含 Xml 的 5.15.2.1。
        self.requires("qt5-qtbase/5.15.2.1")
        self.requires("libaccounts-glib/1.27")

    def validate(self):
        # R32: settings.os 判断必须 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libaccounts-qt only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # PkgConfigDeps 为 glib-2.0/gobject-2.0/libaccounts-glib 生成 .pc
        PkgConfigDeps(self).generate()

    def _cc(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("cpp") or compilers.get("cxx") or "clang++"
        return cc

    def _include_flags(self):
        """收集 qt5-qtbase / libaccounts-glib / glib2 等的 include 路径。"""
        flags = [f"-I{self.source_folder}"]
        for _name, dep in self.dependencies.items():
            for sub in ("include", "src"):
                base = os.path.join(dep.package_folder, sub)
                if os.path.isdir(base):
                    flags.append(f"-I{base}")
                    # Qt5 模块头在各子目录（QtCore/QtXml/QtGui/...），逐一加入
                    for entry in sorted(os.listdir(base)):
                        p = os.path.join(base, entry)
                        if os.path.isdir(p):
                            flags.append(f"-I{p}")
        return " ".join(flags)

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        build = self.build_folder
        cc = self._cc()
        inc = self._include_flags()
        defines = (
            "-DQT_NO_CAST_TO_ASCII -DQT_NO_CAST_FROM_ASCII "
            "-DQT_NO_KEYWORDS -DQ_OS_OHOS"
        )
        moc = os.path.join(self.dependencies["qt5-qtbase"].package_folder, "bin", "moc")

        # 1) moc 处理含 Q_OBJECT 的头（无 Q_OBJECT 的头 moc 输出空文件，无害）
        qobject_headers = [
            "manager.h", "account.h", "account-service.h",
            "application.h", "auth-data.h",
        ]
        moc_objs = []
        for h in qobject_headers:
            moc_src = os.path.join(build, f"moc_{h.replace('.h', '.cpp')}")
            self.run(f'"{moc}" {defines} {inc} "{src}/Accounts/{h}" -o "{moc_src}"')
            obj = moc_src.replace(".cpp", ".o")
            self.run(f'"{cc}" -c {defines} {inc} -fPIC "{moc_src}" -o "{obj}"')
            moc_objs.append(obj)

        # 2) 编译 Accounts 库源文件
        cpp_sources = [
            "manager.cpp", "account.cpp", "account-service.cpp",
            "application.cpp", "auth-data.cpp", "error.cpp",
            "provider.cpp", "service.cpp", "service-type.cpp", "utils.cpp",
        ]
        objs = list(moc_objs)
        for cpp in cpp_sources:
            obj = os.path.join(build, cpp.replace(".cpp", ".o"))
            self.run(f'"{cc}" -c {defines} {inc} -fPIC "{src}/Accounts/{cpp}" -o "{obj}"')
            objs.append(obj)

        # 3) 归档静态库
        self.run(f'ar rcs "{build}/libaccounts-qt5.a" ' + " ".join(objs))

    def package(self):
        src = self.source_folder
        build = self.build_folder
        pkg = self.package_folder
        # 静态库
        self.run(f'mkdir -p "{pkg}/lib" && cp "{build}/libaccounts-qt5.a" "{pkg}/lib/"')
        # 头文件（Accounts/ 子目录下的公共头）
        self.run(f'mkdir -p "{pkg}/include/Accounts"')
        for h in os.listdir(os.path.join(src, "Accounts")):
            if h.endswith(".h"):
                self.run(f'cp "{src}/Accounts/{h}" "{pkg}/include/Accounts/"')

    def package_info(self):
        self.cpp_info.libs = ["accounts-qt5"]
        self.cpp_info.set_property("pkg_config_name", "accounts-qt5")
