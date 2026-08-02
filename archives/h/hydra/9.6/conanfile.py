#!/usr/bin/env python3
"""Conan recipe for THC Hydra 9.6."""

from conan import ConanFile
from conan.tools.files import get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class HydraConan(ConanFile):
    name = "hydra"
    version = "9.6"
    description = "THC Hydra - fast network logon cracker supporting many protocols"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/vanhauser-thc/thc-hydra"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # 远端仓库仅上架 openssl/3.5.6，1.1.1w 未发布会导致依赖解析失败。
        # THC Hydra 自 9.2 起已适配 OpenSSL 3.x API，可直接使用 3.x。
        self.requires("openssl/3.5.6")
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(["--disable-xhydra", "--nostrip"])
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
# OHOS-CI-trigger: re-run build @ 2026-08-02 21:12 (no functional change)
