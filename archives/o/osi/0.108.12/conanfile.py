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
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.microsoft import unix_path


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

    def build_requirements(self):
        if self.settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/cci.latest")

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
        if self.settings_build.os == "Windows":
            coinutils = unix_path(self, coinutils)
        coinutils_include = f"{coinutils}/include/coin"
        coinutils_lib = f"{coinutils}/lib"

        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            tc.update_configure_args({
                "--build": "aarch64-unknown-linux-gnu",
                "--host": "aarch64-unknown-linux-ohos",
            })
        tc.configure_args.extend([
            "--disable-shared",
            "--enable-static",
            "--disable-dependency-tracking",
            f"--with-coinutils-incdir={coinutils_include}",
            f"--with-coinutils-lib=-L{coinutils_lib} -lCoinUtils -lz -lm",
            "--without-glpk",
            "--without-soplex",
            "--without-cplex",
            "--without-mosek",
            "--without-xpress",
            "--without-gurobi",
        ])
        env = tc.environment()
        env.append("CPPFLAGS", f"-I{coinutils_include}")
        if self.settings_build.os == "Windows":
            # Libtool's legacy command-line limit probe can loop for minutes
            # under MSYS. Use the conservative Windows limit explicitly.
            env.define("lt_cv_sys_max_cmd_len", "8192")
        tc.generate(env)

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os == "OHOS":
            for configure in ("configure", os.path.join("Osi", "configure")):
                path = os.path.join(self.source_folder, configure)
                replace_in_file(
                    self,
                    path,
                    "umask 077 && mktemp -d -q",
                    "umask 022 && mktemp -d -q",
                    strict=False,
                )
                replace_in_file(
                    self,
                    path,
                    "umask 077 && mkdir",
                    "umask 022 && mkdir",
                    strict=False,
                )
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        Autotools(self).install()
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        libs = collect_libs(self)
        coinutils_headers = os.path.join(
            self.dependencies["coinutils"].package_folder,
            "include",
            "coin",
        )
        self.cpp_info.libs = ["Osi"] if "Osi" in libs else libs
        self.cpp_info.includedirs = ["include", coinutils_headers]
        self.cpp_info.requires = ["coinutils::coinutils"]
        self.cpp_info.set_property("cmake_file_name", "osi")
        self.cpp_info.set_property("cmake_target_name", "osi::osi")
