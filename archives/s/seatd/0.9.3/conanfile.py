#!/usr/bin/env python3
"""Conan recipe - seatd 0.9.3 (meson).

seatd is a minimal seat management daemon, and provides libseat — a universal
seat management library. This recipe builds both the seatd daemon and libseat.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain, meson_layout


class SeatdConan(ConanFile):
    name = "seatd"
    version = "0.9.3"
    description = "A minimal seat management daemon, and a universal seat management library (libseat)"
    license = "MIT"
    homepage = "https://git.sr.ht/~kennylevinsen/seatd"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "server": [True, False],        # build the seatd daemon
        "seatd_backend": [True, False], # libseat seatd backend
        "builtin": [True, False],       # libseat built-in seatd server
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "server": True,
        "seatd_backend": True,
        "builtin": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")
        # OHOS 平台：无动态库使用场景，删除 shared，强制静态
        if self.settings.os == "OHOS":
            self.options.rm_safe("shared")

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

    def layout(self):
        meson_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = (
            "shared" if self.options.get_safe("shared") else "static"
        )
        # seatd daemon (可执行文件随 meson install 一并安装到 bin/)
        tc.project_options["server"] = "enabled" if self.options.server else "disabled"
        # libseat backends
        tc.project_options["libseat-seatd"] = "enabled" if self.options.seatd_backend else "disabled"
        tc.project_options["libseat-builtin"] = "enabled" if self.options.builtin else "disabled"
        # OHOS has no systemd/elogind. Keep upstream auto-detection on Linux.
        tc.project_options["libseat-logind"] = (
            "auto" if self.settings.os == "Linux" else "disabled"
        )
        # 禁用非必要产物
        tc.project_options["man-pages"] = "disabled"
        tc.project_options["examples"] = "disabled"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.compile()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["seat"]
        self.cpp_info.set_property("pkg_config_name", "libseat")
