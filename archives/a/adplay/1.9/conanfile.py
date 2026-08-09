#!/usr/bin/env python3
"""Conan recipe for adplay 1.9 (AdPlay/UNIX — OPL2 player) on HarmonyOS PC."""

import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class AdplayConan(ConanFile):
    name = "adplay"
    version = "1.9"
    description = "AdPlay/UNIX — console-based OPL2 audio player (AdPlug frontend)"
    license = "GPL-2.0"
    homepage = "https://github.com/adplug/adplay-unix"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # 上游使用 autotools（configure/make）。
        # OHOS CI Worker 网络受限且交叉环境无 autoconf 缓存，直接运行自带脚本。
        self.run(
            f'cd "{self.source_folder}" && ./configure --prefix="{self.package_folder}" '
            "--host=aarch64-unknown-linux-ohos --disable-shared --enable-static",
            env="conanbuild",
        )
        self.run(f'cd "{self.source_folder}" && make -j1', env="conanbuild")
        self.run(f'cd "{self.source_folder}" && make install', env="conanbuild")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
