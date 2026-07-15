#!/usr/bin/env python3
"""Conan recipe — cdo 2.4.0 (Climate Data Operators, autotools).

CDO is a command-line tool for processing climate and forecast data.
Uses autotools build system. config.guess/config.sub are patched
with patch-ohos.sh for HarmonyOS platform recognition (E007).
"""
import os

from conan import ConanFile
from conan.tools.files import get, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CdoConan(ConanFile):
    name = "cdo"
    version = "2.4.0"
    description = "Climate Data Operators — command-line tools for processing climate and forecast data"
    license = "GPL-2.0-only"
    homepage = "https://code.mpimet.mpg.de/projects/cdo"
    url = ""
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

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
        # R26: Static build for system-name libraries
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--without-netcdf")
        tc.configure_args.append("--without-hdf5")
        tc.configure_args.append("--without-szlib")
        tc.configure_args.append("--disable-dependency-tracking")
        tc.generate()

    def build(self):
        # R33: Get compiler from Conan conf, not shell env
        cc = self.conf.get("tools.build:compiler_executables:c", "clang", check_type=str)
        cxx = self.conf.get("tools.build:compiler_executables:cpp", "clang++", check_type=str)
        # E007: Patch config.guess/config.sub for HarmonyOS via helper script
        script = os.path.join(self.source_folder, "patches", "patch-ohos.sh")
        if os.path.exists(script):
            self.run(f"bash {script} {self.source_folder}")
        # Build with autotools
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Ensure binary has execute permission
        self.run(f"chmod +x {self.package_folder}/bin/cdo")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]