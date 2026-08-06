#!/usr/bin/env python3
"""Conan recipe for libpipeline 1.5.8 on HarmonyOS PC (aarch64)."""
import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibpipelineConan(ConanFile):
    name = "libpipeline"
    version = "1.5.8"
    description = "C library for manipulating pipelines of subprocesses"
    license = "GPL-3.0-or-later"
    homepage = "https://savannah.nongnu.org/projects/libpipeline/"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # umask 077 → 022 already applied via 0003-configure.patch
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["pipeline"]
        self.cpp_info.set_property("pkg_config_name", "libpipeline")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = []
