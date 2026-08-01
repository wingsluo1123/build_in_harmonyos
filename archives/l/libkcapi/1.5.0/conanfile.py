#!/usr/bin/env python3
"""Conan recipe for libkcapi 1.5.0."""

import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibkcapiConan(ConanFile):
    name = "libkcapi"
    version = "1.5.0"
    description = "Linux Kernel Crypto API userspace library"
    license = "BSD-3-Clause"
    homepage = "https://github.com/smuellerDD/libkcapi"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    exports_sources = "patches/*", "prebuilt.tar.gz"

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.generate()

    def build(self):
        prebuilt = os.path.join(self.source_folder, "prebuilt.tar.gz")
        self.run(f'tar xzf "{prebuilt}" -C "{self.source_folder}"')
        apply_conandata_patches(self)

        # Keep make from regenerating these files on workers without aclocal.
        for name in ("aclocal.m4", "configure", "Makefile.in"):
            os.utime(os.path.join(self.source_folder, name), None)

        if self.settings.os == "OHOS":
            shell = "#!/data/service/hnp/bin/bash"
            for name in ("configure", "compile", "config.guess", "config.sub",
                         "depcomp", "install-sh", "missing"):
                path = os.path.join(self.source_folder, name)
                replace_in_file(self, path, "#!/bin/sh", shell, strict=False)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["kcapi"]
        self.cpp_info.set_property("cmake_file_name", "libkcapi")
        self.cpp_info.set_property("cmake_target_name", "libkcapi::libkcapi")
# OHOS-CI-trigger: re-run build (no functional change)
