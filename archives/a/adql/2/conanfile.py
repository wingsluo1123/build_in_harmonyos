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
    version = "2"
    description = "libadql — C++ parser for IVOA ADQL 2.0 queries"
    license = "GPL-2.0"
    homepage = "https://github.com/Caltech-IPAC/libadql"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # 上游使用 waf 构建系统（自带 waf 脚本）。
        # OHOS CI Worker 网络受限且 waf 需 python2 兼容，改用显式 python 调用。
        python = "python"
        self.run(
            f'"{python}" waf configure --prefix="{self.package_folder}"',
            cwd=self.source_folder,
        )
        self.run(f'"{python}" waf build', cwd=self.source_folder)
        self.run(f'"{python}" waf install', cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["adql"]
        self.cpp_info.includedirs = ["include"]
