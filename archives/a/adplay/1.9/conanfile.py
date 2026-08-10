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
        # GitHub archive tarball 从不含 configure（只是 git tree 快照），
        # 源码树只有 configure.ac，必须先 autoreconf 自举生成 configure。
        import os as _os

        if not _os.path.isfile(_os.path.join(self.source_folder, "configure")):
            self.output.info(
                "源码树无 configure（GitHub archive 常见），先 autoreconf 自举"
            )
            self.run(
                f'cd "{self.source_folder}" && autoreconf -fi',
                env="conanbuild",
            )
        self.run(
            f'cd "{self.source_folder}" && ./configure --prefix="{self.package_folder}" '
            "--host=aarch64-unknown-linux-ohos --disable-shared --enable-static",
            env="conanbuild",
        )
        self.run(f'cd "{self.source_folder}" && make -j1', env="conanbuild")
        self.run(f'cd "{self.source_folder}" && make install', env="conanbuild")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
