#!/usr/bin/env python3
"""Conan recipe for aider 0.86.2 — AI pair programming CLI（纯 Python PEP 517 包）。

aider 是纯 Python noarch 应用（aider-chat 0.86.2，PEP 517/setuptools，
console entry: aider = aider.main:main）。构建系统为 setuptools.build_meta。
本配方参照仓库纯 Python 包先例（alabaster/adman）：
- 从官方 GitHub tag tarball 取源（R39）；
- PEP 517 构建子进程需显式 PATH/CC（知识图谱 E217 已验证事实）；
- 本体以 --no-deps 安装到 staging，运行时依赖经 PyPI 社区源声明；
- 依赖闭环状态见 manifest/notes（社区源缺 16 个精确 pin，未达成时不得标记 published）。
"""
import os
import sys

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class AiderConan(ConanFile):
    name = "aider"
    version = "0.86.2"
    description = "Aider is AI pair programming in your terminal"
    license = "Apache-2.0"
    homepage = "https://github.com/Aider-AI/aider"
    url = "https://github.com/Aider-AI/aider"
    package_type = "application"

    # Pure Python noarch: no C/C++ compile (PEP 517 build needs clang for sdists)
    # settings 含 os/arch/compiler/build_type 四项（W3 L0p gate 要求，防 profile 不兼容）
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)
        # 随配方导出 OHOS 社区源可用版本的重基依赖清单（build() 中安装到 staging）
        from conan.tools.files import copy as _copy
        _copy(self, "requirements-ohos.txt", src=os.path.dirname(__file__), dst=self.export_sources_folder)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _py_ver(self):
        return f"python{sys.version_info.major}.{sys.version_info.minor}"

    def _prepend_clang(self):
        # PEP 517 / 原生扩展构建子进程需要 clang 在 PATH 与 CC（E217 已验证事实）。
        # conanrun/conanbuild 环境不一定注入 buildenv PATH，这里显式前置。
        clang_bin = "/data/service/hnp/bin"
        return f'export PATH="{clang_bin}:$PATH"; export CC="{clang_bin}/clang"; export CXX="{clang_bin}/clang++";'

    def build(self):
        apply_conandata_patches(self)

        python_exe = sys.executable
        src_dir = self.source_folder
        staging = os.path.join(self.build_folder, "staging")
        os.makedirs(staging, exist_ok=True)

        # 构建期依赖：setuptools>=68 + setuptools_scm[toml]>=8（PEP 517 build backend）
        # OHOS profile buildenv 已提供 PATH（/data/service/hnp/bin 含 clang），无需手动 env dict
        self.run(
            f'{python_exe} -m pip install --break-system-packages '
            f'--timeout 120 --retries 3 --ignore-installed "setuptools>=68" "setuptools_scm[toml]>=8"',
            env="conanbuild",
        )

        # 运行时依赖：包内自带，避免 test_package 依赖外部预装环境。
        # 版本清单为 OHOS 社区源可用版本的重基清单（requirements-ohos.txt，export_sources 随配方提供，
        # source() 后位于 self.source_folder），基于官方 requirements.txt 仅替换社区源缺失的 16 个精确 pin。
        req_file = os.path.join(self.source_folder, "requirements-ohos.txt")
        if os.path.exists(req_file):
            self.run(
                f'{self._prepend_clang()} {python_exe} -m pip install --break-system-packages '
                f'--timeout 120 --retries 3 --ignore-installed --prefix="{staging}" -r "{req_file}"',
                env="conanbuild",
            )
        else:
            raise Exception(f"requirements-ohos.txt not found in source_folder={self.source_folder}")

        # 本体以 --no-deps 安装到 staging（依赖已在上一步装入同一 staging）
        # GitHub tag tarball 无 .git 元数据，setuptools_scm 无法推断版本：
        # 使用 SETUPTOOLS_SCM_PRETEND_VERSION_FOR_AIDER_CHAT=0.86.2 显式指定（setuptools_scm 官方机制）
        self.run(
            f'{self._prepend_clang()} SETUPTOOLS_SCM_PRETEND_VERSION_FOR_AIDER_CHAT=0.86.2 '
            f'{python_exe} -m pip install --break-system-packages --no-deps '
            f'--prefix="{staging}" "{src_dir}"',
            env="conanbuild",
        )

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        py_ver = self._py_ver()
        site_dst = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        bin_dst = os.path.join(self.package_folder, "bin")

        # Locate site-packages under staging
        site_src = None
        for candidate in (
            os.path.join(staging, "lib", py_ver, "site-packages"),
            os.path.join(staging, "lib", py_ver, "dist-packages"),
            os.path.join(staging, "local", "lib", py_ver, "site-packages"),
            os.path.join(staging, "local", "lib", py_ver, "dist-packages"),
        ):
            if os.path.isdir(candidate) and os.path.isdir(os.path.join(candidate, "aider")):
                site_src = candidate
                break
        if site_src is None:
            raise Exception(f"aider site-packages not found under staging={staging}")

        copy(self, "*", src=site_src, dst=site_dst)

        # GitHub 源码目录 pip install 时 setuptools packages.find include=["aider"]
        # 仅打包顶层包，coders/queries/website/resources 等子包在 wheel 中丢失
        # （PyPI sdist 安装才完整）。显式从源码树补齐全部子包，保证
        # aider.coders / aider.resources 可导入（CLI 启动依赖）。
        src_aider = os.path.join(self.source_folder, "aider")
        dst_aider = os.path.join(site_dst, "aider")
        if os.path.isdir(src_aider):
            for sub in ("coders", "queries", "resources", "website"):
                sub_src = os.path.join(src_aider, sub)
                if os.path.isdir(sub_src):
                    copy(self, "*", src=sub_src, dst=os.path.join(dst_aider, sub))

        for bin_src in (
            os.path.join(staging, "bin"),
            os.path.join(staging, "local", "bin"),
        ):
            if os.path.isdir(bin_src):
                copy(self, "*", src=bin_src, dst=bin_dst)

        for lic_name in ("LICENSE.txt", "LICENSE"):
            src = os.path.join(self.source_folder, lic_name)
            if os.path.isfile(src):
                copy(self, lic_name, src=self.source_folder,
                     dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]

        site_packages = os.path.join(
            self.package_folder, "lib", self._py_ver(), "site-packages"
        )
        self.runenv_info.append_path("PYTHONPATH", site_packages)
        self.buildenv_info.append_path("PYTHONPATH", site_packages)
        bin_path = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_path):
            self.runenv_info.append_path("PATH", bin_path)
            self.buildenv_info.append_path("PATH", bin_path)
