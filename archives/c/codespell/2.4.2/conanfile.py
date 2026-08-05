#!/usr/bin/env python3
"""Conan recipe — codespell 2.4.2 (pure Python, setuptools + setuptools_scm).

鸿蒙适配说明：
- 纯 Python 项目，无需 C 编译器
- 使用 pip wheel 构建 + pip install 安装，跳过依赖检查
- 通过 build isolation 让 pip 自动安装 setuptools_scm 等构建依赖
- PIP_TARGET= 覆盖系统 pip 配置中可能存在的 PIP_TARGET 环境变量
- codespell 是命令行工具（application 类型），需要 commands.json 声明（R38）
"""
import os
import sys
import glob

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CodespellConan(ConanFile):
    name = "codespell"
    version = "2.4.2"
    description = "Fix common misspellings in text files"
    license = "GPL-2.0-only"
    homepage = "https://github.com/codespell-project/codespell"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # 纯 Python 项目：用 pip wheel 构建（build isolation 自动安装 setuptools_scm）
        self.run(
            f'PIP_TARGET="" SETUPTOOLS_SCM_PRETEND_VERSION_FOR_codespell=2.4.2 '
            f'python3 -m pip wheel --no-deps -w "{self.build_folder}" .',
            cwd=self.source_folder,
        )

    def package(self):
        # 找到构建好的 wheel 并安装
        wheels = glob.glob(os.path.join(self.build_folder, "codespell-*.whl"))
        if not wheels:
            raise Exception("No wheel found in build folder")
        wheel = wheels[0]
        self.run(
            f'PIP_TARGET="" python3 -m pip install --no-deps '
            f'--prefix="{self.package_folder}" "{wheel}"',
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        # 设置 PYTHONPATH 使 codespell CLI 能找到 codespell_lib
        pyver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_pkgs = os.path.join(self.package_folder, "lib", pyver, "site-packages")
        self.runenv_info.append_path("PYTHONPATH", site_pkgs)
