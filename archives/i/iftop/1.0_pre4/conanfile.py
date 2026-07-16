#!/usr/bin/env python3
"""Conan recipe for iftop 1.0_pre4 — network bandwidth monitoring tool.

iftop displays a table of current bandwidth usage by host on a network
interface. It uses libpcap for packet capture and ncurses for its terminal
(curses) UI.

Build system: autotools (configure + make)
Product: `iftop` executable (terminal tool — no linkable library)
Dependencies: libpcap, ncurses
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class IftopConan(ConanFile):
    name = "iftop"
    version = "1.0_pre4"
    description = "iftop — display bandwidth usage on an interface by host"
    license = "GPL-2.0-or-later"
    homepage = "http://www.ex-parrot.com/pdw/iftop/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        # OHOS 平台: iftop 是终端可执行工具, 无需 shared 库选项
        if self.settings.os == "OHOS":
            self.options.rm_safe("shared")
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")
            self.options.rm_safe("shared")

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("libpcap/1.10.6")
        self.requires("ncurses/6.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # iftop 是可执行文件, 非可链接库
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
