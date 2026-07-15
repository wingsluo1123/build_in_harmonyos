#!/usr/bin/env python3
"""Conan recipe for libbsd 0.12.2."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibbsdConan(ConanFile):
    name = "libbsd"
    version = "0.12.2"
    description = "commonly-used BSD functions not implemented by all libc"
    license = "BSD-3-Clause"
    homepage = "https://libbsd.freedesktop.org"
    url = ""

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libmd/1.1.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # OHOS aarch64 的 config.guess/sub 不识别 linux-ohos 三元组，显式指定
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["bsd"]
        self.cpp_info.set_property("pkg_config_name", "libbsd")