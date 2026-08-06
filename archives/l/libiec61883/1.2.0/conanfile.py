#!/usr/bin/env python3
"""Conan recipe for libiec61883 1.2.0 (Autotools).

Layer 2 dependency: depends on libraw1394/2.1.2.

R26: Not a system-name library; shared is OK but default static.
R32: settings.os check uses `in ("Linux", "OHOS")`.
E007: config.guess/config.sub patched for HarmonyOS.
umask 077 → 022 fix for HMDFS permission issue (via patch 0003).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    get,
    copy,
    rm,
    apply_conandata_patches,
    export_conandata_patches,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Libiec61883Conan(ConanFile):
    name = "libiec61883"
    version = "1.2.0"
    description = "IEC 61883 (IEC 61883) streaming for IEEE 1394"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.kernel.org/pub/linux/libs/ieee1394/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if str(self.settings.os) == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libiec61883 supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        self.requires("libraw1394/2.1.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

        # Copy license
        copy(
            self,
            "COPYING*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

        # Remove libtool archives
        rm(self, "*.la", os.path.join(self.package_folder, "lib"), recursive=True)
        if not self.options.shared:
            rm(self, "*.so*", os.path.join(self.package_folder, "lib"), recursive=True)
        else:
            rm(self, "*.a", os.path.join(self.package_folder, "lib"), recursive=True)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libiec61883")
        self.cpp_info.set_property("cmake_target_name", "libiec61883::libiec61883")
        self.cpp_info.set_property("pkg_config_name", "libiec61883")
        self.cpp_info.libs = ["iec61883"]
        self.cpp_info.requires = ["libraw1394::libraw1394"]
