#!/usr/bin/env python3
"""Conan recipe — oarc-dsc-datatool 1.4.2 (setuptools, pure Python).

dsc_datatool (DSC DataTool) is a pure Python package providing tools to
process DNS Statistics Collector (DSC) data. It is the main Python module
for the command line tool ``dsc-datatool``. The package uses setuptools
and is installed via ``pip install .``. No C extensions are compiled.

R32: settings.os 判断使用 in ("Linux", "OHOS").
R33: build() 不依赖裸 shell 环境变量; Python from sys.executable.
R34: test_package 实质性测试 (module import + version + core classes + functional).
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import get, copy


class OarcDscDatatoolConan(ConanFile):
    name = "oarc-dsc-datatool"
    version = "1.4.2"
    description = ("Python 3 tools to process DNS Statistics Collector "
                   "(DSC) data")
    license = "BSD-3-Clause"
    homepage = "https://github.com/DNS-OARC/dsc-datatool"
    url = "https://github.com/DNS-OARC/dsc-datatool"
    topics = ("dns", "dsc", "datatool", "oarc", "python")

    package_type = "library"
    # 纯 Python 包：只需 os/arch 标识平台，无编译器依赖
    settings = "os", "arch"

    # Conan 2.x: library 类型必须声明 shared option（纯 Python 包固定 False）
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        pass

    def validate(self):
        """R32: OHOS 平台兼容 — 在 validate() 中拒绝不支持的 OS."""
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}. "
                f"oarc-dsc-datatool only supports Linux and OHOS."
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        """Install dsc_datatool via pip from local source (no remote download).

        R33: uses sys.executable (Conan's Python), not bare ${CC}/${CFLAGS}.
        --no-deps: we don't want pip to pull runtime deps from PyPI; they are
                   declared in setup.py's install_requires for reference only.
        --prefix:  installs into a staging prefix; package() copies to
                   package_folder.
        """
        prefix = os.path.join(self.build_folder, "package")
        python = sys.executable
        self.run(
            f"{python} -m pip install . --prefix={prefix} --no-deps",
            cwd=self.source_folder,
        )

    def package(self):
        """Copy staged pip install into Conan package folder."""
        prefix = os.path.join(self.build_folder, "package")
        if not os.path.isdir(prefix):
            raise ConanException(
                f"Package directory not found: {prefix}, nothing to package"
            )
        for item in os.listdir(prefix):
            src = os.path.join(prefix, item)
            dst = os.path.join(self.package_folder, item)
            if os.path.isdir(src):
                copy(self, "*", src=src, dst=dst)
            else:
                copy(self, item, src=prefix, dst=self.package_folder)

    def package_info(self):
        """Export site-packages PYTHONPATH for downstream consumers.

        Pure Python package — no C libraries, no include dirs.
        Uses runenv_info.append_path to inject PYTHONPATH (Conan 2.x idiom).
        """
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = []

        python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_pkgs = os.path.join("lib", python_version, "site-packages")
        site_pkgs_path = os.path.join(self.package_folder, site_pkgs)
        self.runenv_info.append_path("PYTHONPATH", site_pkgs_path)
        self.output.info(f"oarc-dsc-datatool installed: {site_pkgs}/dsc_datatool/")
