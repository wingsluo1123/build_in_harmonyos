#!/usr/bin/env python3
"""Conan recipe — xkbcommon 1.13.2 (Meson build).

libxkbcommon: XKB keymap creation/lookup library.
OHOS 适配：关闭 X11(xcb)/Wayland/tools/xkbregistry/bash-completion 可选功能，
仅构建核心库 libxkbcommon（wlroots/wayfire 所需）。xkbcommon-x11 与
xkbregistry 为独立附加库，wlroots/wayfire 不依赖，关闭不影响消费方。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


class XkbcommonConan(ConanFile):
    name = "xkbcommon"
    version = "1.13.2"
    description = "Library to create keymaps and to handle keymap lookup (XKB)"
    license = "MIT"
    homepage = "https://github.com/xkbcommon/libxkbcommon"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 核心库无强制外部依赖；可选功能（x11/xkbregistry）已关闭
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # R26: 系统同名库默认静态
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # OHOS 无 X11/xcb、无 wayland tools 依赖，关闭可选功能
        tc.project_options["enable-x11"] = "false"
        tc.project_options["enable-wayland"] = "false"
        tc.project_options["enable-tools"] = "false"
        tc.project_options["enable-xkbregistry"] = "false"
        tc.project_options["enable-bash-completion"] = "false"
        tc.generate()
        # E1124: Meson probes a static archiver while detecting the C toolchain;
        # the native file names no `ar`, and CI worker PATHs carry no bare
        # llvm-ar/ar -> "Unknown linker(s): [['llvm-ar']]" at setup. Pin the
        # archiver next to the compiler the profile already pins absolutely
        # (bstring/c-stdaux precedent: /data/service/hnp/bin/ar is CI-proven).
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        with open(native_file) as f:
            content = f.read()
        marker = "[binaries]\nc ="
        if marker not in content:
            raise ConanInvalidConfiguration(
                "meson native file layout changed: '[binaries]\\nc =' not found"
            )
        ar_abs = "/data/service/hnp/bin/ar"
        if "ar =" not in content.split("[binaries]", 1)[1].split("\n\n", 1)[0]:
            content = content.replace(
                marker, "[binaries]\nar = '{}'".format(ar_abs) + "\nc =", 1
            )
            with open(native_file, "w") as f:
                f.write(content)
            self.output.info("  [ok] pinned meson archiver to " + ar_abs)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["xkbcommon"]
        self.cpp_info.set_property("pkg_config_name", "xkbcommon")
