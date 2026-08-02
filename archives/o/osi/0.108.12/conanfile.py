#!/usr/bin/env python3
"""Conan recipe for Osi 0.108.12."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    collect_libs,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class OsiConan(ConanFile):
    name = "osi"
    version = "0.108.12"
    description = "COIN-OR Open Solver Interface"
    license = "EPL-2.0"
    homepage = "https://github.com/coin-or/Osi"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [False]}
    default_options = {"shared": False}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("osi supports Linux and OHOS")

    def requirements(self):
        self.requires(
            "coinutils/2.11.13",
            transitive_headers=True,
            transitive_libs=True,
        )

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        export_conandata_patches(self)

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        coinutils = self.dependencies["coinutils"].package_folder

        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-ohos",
            ])
        tc.configure_args.extend([
            "--disable-shared",
            "--enable-static",
            "--disable-dependency-tracking",
            f"--with-coin-instdir={coinutils}",
            "--without-glpk",
            "--without-soplex",
            "--without-cplex",
            "--without-mosek",
            "--without-xpress",
            "--without-gurobi",
        ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        Autotools(self).install()
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        libs = collect_libs(self)
        self.cpp_info.libs = ["Osi"] if "Osi" in libs else libs
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "osi")
        self.cpp_info.set_property("cmake_target_name", "osi::osi")
