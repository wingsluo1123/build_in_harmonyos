#!/usr/bin/env python3
"""Conan recipe — wf-utils 0.4.0 (Meson build).

wf-utils: Wayfire 基础工具库（action/condition/lexer/parser/rule/variant）。
上游无正式 release tag（meson project version 0.4.0），源码为 wayfire v0.10.0
submodule 引用 commit 3ef27d1f76b5f3d1f34305bff12b3174e81727c2。无外部依赖。
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


class WfUtilsConan(ConanFile):
    name = "wf-utils"
    version = "0.4.0"
    description = "Basic utilities library for Wayfire"
    license = "MIT"
    homepage = "https://github.com/WayfireWM/wf-utils"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # 无外部依赖

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # E1124: CI worker PATH 无 llvm-ar（本地 PATH 有 ar 会掩盖问题），meson setup
        # 探测静态归档器报 "Unknown linker(s): [['llvm-ar']]"。显式钉死 ar 绝对路径。
        ar_path = "/data/service/hnp/bin/ar"
        if os.path.isfile(ar_path):
            tc.ar = ar_path
        tc.generate()
        # E1014: OHOS 上 meson sanity check 编译的 C++ 二进制依赖 libc++_shared.so，
        # 该库位于 <llvm>/lib/aarch64-linux-ohos（profile 的 LD_LIBRARY_PATH 只覆盖
        # <llvm>/lib 根目录），不 prepend 会导致 meson configure 报
        # "Executables created by cpp compiler ... are not runnable"。
        if self.settings.os == "OHOS":
            for cpp_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib/aarch64-linux-ohos"
                )
            ):
                if os.path.isdir(cpp_lib):
                    cur = os.environ.get("LD_LIBRARY_PATH", "")
                    os.environ["LD_LIBRARY_PATH"] = (
                        cpp_lib + os.pathsep + cur if cur else cpp_lib
                    )

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["wf-utils"]
        self.cpp_info.set_property("pkg_config_name", "wf-utils")
