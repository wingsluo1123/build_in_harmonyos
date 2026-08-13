#!/usr/bin/env python3
"""Conan recipe for pydl 1.0.1 — IDL 天文例程的 Python 移植（纯 Python noarch）。

pydl 是纯 Python 库（Astropy affiliated），无 C/C++ 编译产物，
构建后端为 setuptools。上游 sdist 含 pytest 测试（conftest.py +
pydl/tests/），本配方按 R28 在 test_package 补全消费者验证。
运行时依赖 astropy/scipy。
"""
import os
import sys

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PydlConan(ConanFile):
    name = "pydl"
    version = "1.0.1"
    description = "Library of IDL astronomy routines converted to Python"
    license = "BSD-3-Clause"
    homepage = "https://github.com/weaverba137/pydl"
    url = ""

    # Pure Python noarch: compiler/build_type declared to satisfy OHOS
    # profile requirements (L0p needs all four: os/arch/compiler/build_type)
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _py_ver(self):
        return f"python{sys.version_info.major}.{sys.version_info.minor}"

    def build(self):
        apply_conandata_patches(self)

        python_exe = sys.executable
        src_dir = self.source_folder
        staging = os.path.join(self.build_folder, "staging")
        os.makedirs(staging, exist_ok=True)

        # Build deps: setuptools/wheel（构建后端）
        self.run(
            f'{python_exe} -m pip install --break-system-packages '
            f'--timeout 120 --retries 3 setuptools wheel',
        )

        # Install into staging via --prefix
        self.run(
            f'{python_exe} -m pip install --break-system-packages --no-deps '
            f'--prefix="{staging}" "{src_dir}"',
        )

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        py_ver = self._py_ver()
        site_dst = os.path.join(
            self.package_folder, "lib", py_ver, "site-packages"
        )
        bin_dst = os.path.join(self.package_folder, "bin")

        site_src = None
        for candidate in (
            os.path.join(staging, "lib", py_ver, "site-packages"),
            os.path.join(staging, "lib", py_ver, "dist-packages"),
            os.path.join(staging, "local", "lib", py_ver, "site-packages"),
            os.path.join(staging, "local", "lib", py_ver, "dist-packages"),
            os.path.join(staging, "lib64", py_ver, "site-packages"),
        ):
            if os.path.isdir(candidate) and os.path.isdir(
                os.path.join(candidate, "pydl")
            ):
                site_src = candidate
                break
        if site_src is None:
            raise Exception(
                f"pydl site-packages not found under staging={staging}"
            )

        copy(self, "*", src=site_src, dst=site_dst)

        for bin_src in (
            os.path.join(staging, "bin"),
            os.path.join(staging, "local", "bin"),
        ):
            if os.path.isdir(bin_src):
                copy(self, "*", src=bin_src, dst=bin_dst)

        for lic_name in ("LICENSE.rst", "LICENSE", "LICENSE.txt"):
            src = os.path.join(self.source_folder, lic_name)
            if os.path.isfile(src):
                copy(
                    self,
                    lic_name,
                    src=self.source_folder,
                    dst=os.path.join(self.package_folder, "licenses"),
                )

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
