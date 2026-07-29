#!/usr/bin/env python3
"""Conan recipe — nettle 3.10.2 (Autotools)"""

import os
import shutil

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class NettleConan(ConanFile):
    name = "nettle"
    version = "3.10.2"
    description = "Low-level cryptographic library"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.lysator.liu.se/~nisse/nettle/"
    url = "https://git.lysator.liu.se/nettle/nettle"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    win_bash = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gmp/6.3.0")

    def build_requirements(self):
        if self.settings_build.os == "Windows":
            self.tool_requires("msys2/cci.latest")

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        tc.configure_args.append("--disable-documentation")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._prepare_autotools_environment()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "nettle")
        self.cpp_info.set_property("cmake_target_name", "nettle::nettle")
        self.cpp_info.set_property("pkg_config_name", "nettle")

        nettle = self.cpp_info.components["libnettle"]
        nettle.libs = ["nettle"]
        nettle.set_property("cmake_target_name", "nettle::libnettle")
        nettle.set_property("pkg_config_name", "nettle")

        hogweed = self.cpp_info.components["hogweed"]
        hogweed.libs = ["hogweed"]
        hogweed.requires = ["libnettle", "gmp::gmp"]
        hogweed.set_property("cmake_target_name", "nettle::hogweed")
        hogweed.set_property("pkg_config_name", "hogweed")

    def _prepare_autotools_environment(self):
        bash_path = shutil.which("bash") if self.settings.os != "Windows" else None
        if bash_path is not None:
            os.environ["CONFIG_SHELL"] = bash_path
            os.environ["SHELL"] = bash_path

        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TEMP"] = tmpdir
        os.environ["TMP"] = tmpdir
