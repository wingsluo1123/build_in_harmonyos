#!/usr/bin/env python3
"""Conan recipe for varlink 24.0.1 — libvarlink（Varlink 协议 C 实现，Meson）.

Varlink 是接口描述格式与 IPC 协议；本包为 C 实现库 libvarlink（含
命令行工具 varlink）。Meson 构建，无外部硬依赖（仅 libm）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class VarlinkConan(ConanFile):
    name = "varlink"
    version = "24.0.1"
    description = "libvarlink — C implementation of the Varlink protocol"
    license = "Apache-2.0"
    homepage = "https://varlink.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.generate()
        # CI #89843：meson 的 archiver 探测经 PATH 找不到 llvm-ar（conan 的
        # meson.configure() 未把 build env 的 PATH 传给 meson），依次尝试
        # llvm-ar-15/llvm-ar/ar/gar 均失败。在 native 文件 [binaries] 显式
        # 注入 ar 绝对路径（与 clang 同目录的 llvm-ar），绕过 PATH 依赖。
        native = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if os.path.exists(native):
            conf = self.conf.get("tools.build:compiler_executables", default={}) or {}
            cc = conf.get("c", "clang") if isinstance(conf, dict) else "clang"
            ar = os.path.join(os.path.dirname(cc), "llvm-ar")
            with open(native) as f:
                content = f.read()
            if "ar =" not in content:
                content = content.replace("[binaries]", "[binaries]\nar = '%s'" % ar, 1)
                with open(native, "w") as f:
                    f.write(content)

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # libvarlink.so / libvarlink.a（lib/meson.build：shared_library 名 libvarlink）
        self.cpp_info.libs = ["varlink"]
        self.cpp_info.set_property("pkg_config_name", "libvarlink")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
