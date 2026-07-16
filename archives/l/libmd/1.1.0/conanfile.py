#!/usr/bin/env python3
"""Conan recipe for libmd 1.1.0.
OHOS 上 HMDFS 禁止执行用户文件 (E046)，config.status 创建临时 awk 脚本会失败。
解决：configure 后在 config.status 中用 $AWK -f 替换直接执行。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibmdConan(ConanFile):
    name = "libmd"
    version = "1.1.0"
    description = "Message Digest functions from BSD systems"
    license = "BSD-3-Clause"
    homepage = "https://libbsd.freedesktop.org"
    url = ""

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # OHOS HMDFS noexec (E046): config.status 中临时 awk 脚本无法直接执行,
        # 用 $AWK -f 方式运行
        self.run(r"sed -i 's|\./conftmp[^ ]*/subs1\.awk|$AWK -f &|g' config.status",
                 cwd=self.source_folder, ignore_errors=True)
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["md"]
        self.cpp_info.set_property("pkg_config_name", "libmd")