#!/usr/bin/env python3
"""Conan recipe — arm-none-eabi-binutils 2.46.1 (HarmonyOS PC)
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import VirtualBuildEnv
import os


class ArmnoneeabibinutilsConan(ConanFile):
    name = "arm-none-eabi-binutils"
    version = "2.46.1"
    description = "GNU Binutils for arm-none-eabi cross development (HarmonyOS PC)"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/binutils/"

    package_type = "application"

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
        tc.configure_args.append("--target=arm-none-eabi")
        tc.configure_args.append("--disable-nls")
        tc.configure_args.append("--disable-werror")
        tc.configure_args.append("--disable-gdb")
        tc.configure_args.append("--disable-gdbserver")
        tc.configure_args.append("--disable-libdecnumber")
        tc.configure_args.append("--disable-readline")
        tc.configure_args.append("--disable-sim")
        # Bypass config.guess detection on OHOS
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Fix umask 077 → umask 022 for HMDFS compatibility
        self.run("find . -name configure -exec sed -i 's/umask 077/umask 022/g' {} +",
                 cwd=self.source_folder)
        autotools = Autotools(self)
        autotools.configure(build_script_folder=self.source_folder)
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["arm-none-eabi-binutils"]