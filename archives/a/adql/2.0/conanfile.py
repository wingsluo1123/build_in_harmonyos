#!/usr/bin/env python3
"""Conan recipe for adql 2 (libadql — ADQL 2.0 parser) on HarmonyOS PC."""

import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class AdqlConan(ConanFile):
    name = "adql"
    version = "2.0"
    description = "libadql — C++ parser for IVOA ADQL 2.0 queries"
    license = "GPL-2.0"
    homepage = "https://github.com/Caltech-IPAC/libadql"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # 上游使用 waf 构建系统。libadql 源码树中的 waf 脚本文件名是
        # waf-1.7.9 / waf-2.0.23（不带版本号的可执行文件并不存在），
        # 直接用 `waf` 调用会得到 Error 127 (command not found)。
        # 选用较新的 waf-2.0.23，并用 python 显式调用（CI 的 python 兼容）。
        python = "python"
        self.run(
            f'"{python}" waf-2.0.23 configure --prefix="{self.package_folder}"',
            cwd=self.source_folder,
        )
        self.run(f'"{python}" waf-2.0.23 build', cwd=self.source_folder)
        self.run(f'"{python}" waf-2.0.23 install', cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["adql"]
        self.cpp_info.includedirs = ["include"]
