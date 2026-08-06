#!/usr/bin/env python3
"""Conan recipe - seatd 0.9.3 (meson).

seatd is a minimal seat management daemon, and provides libseat — a universal
seat management library. This recipe builds both the seatd daemon and libseat.
"""
import os

from conan import ConanFile
from conan.tools.files import get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


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

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.settings.os == "OHOS":
            self.options.shared = False
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

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

        # musl 系 sysroot 的 CMSG_NXTHDR() 宏在展开处触发 -Wsign-compare，
        # 该告警源自系统头文件而非 seatd 代码。seatd 以 werror=true 构建，
        # 因此用 -Dwerror=false 整体关闭 warnings-as-errors（与上游 0.9.1
        # 配方一致的做法），无需改任何源码、不加平台条件编译。
        tc.project_options["werror"] = "false"
        tc.generate()

        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c", "")
        bindir = os.path.dirname(compiler) if os.path.sep in compiler else ""
        ar = executables.get("ar") or (os.path.join(bindir, "llvm-ar") if bindir else "")
        ranlib = executables.get("ranlib") or (
            os.path.join(bindir, "llvm-ranlib") if bindir else ""
        )
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if ar and os.path.isfile(ar) and os.path.isfile(native_file):
            with open(native_file, encoding="utf-8") as stream:
                content = stream.read()
            if "\nar =" not in content and "[binaries]\n" in content:
                tools = f"[binaries]\nar = '{ar}'\n"
                if ranlib and os.path.isfile(ranlib):
                    tools += f"ranlib = '{ranlib}'\n"
                content = content.replace("[binaries]\n", tools, 1)
                with open(native_file, "w", encoding="utf-8") as stream:
                    stream.write(content)

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["seat"]
        self.cpp_info.set_property("pkg_config_name", "libseat")
