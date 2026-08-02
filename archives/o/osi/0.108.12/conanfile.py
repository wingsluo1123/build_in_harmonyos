#!/usr/bin/env python3
"""Conan recipe for Osi 0.108.12."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import collect_libs, copy, get, load, save
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

    def _patch_config_scripts(self):
        for script in ("config.guess", "Osi/config.guess"):
            path = os.path.join(self.source_folder, script)
            if os.path.exists(path):
                self.run(
                    r"""sed -i '/^case $UNAME_SYSTEM in$/a\    HarmonyOS|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl;;' """
                    + f"'{path}'"
                )
                self.run(
                    r"""sed -i '/^case "${UNAME_SYSTEM}" in$/a\    HarmonyOS|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl;;' """
                    + f"'{path}'"
                )

        for script in ("config.sub", "Osi/config.sub"):
            path = os.path.join(self.source_folder, script)
            if not os.path.exists(path):
                continue

            contents = load(self, path)
            if "linux-ohos" in contents:
                continue

            original_contents = contents
            replacements = (
                (
                    "linux-musl* | linux-uclibc*",
                    "linux-musl* | linux-ohos* | linux-uclibc*",
                ),
                (
                    "linux-gnu* | linux-dietlibc | linux-uclibc*",
                    "linux-gnu* | linux-ohos* | linux-dietlibc | linux-uclibc*",
                ),
                (
                    "linux-gnu* | linux-dietlibc* | linux-uclibc*",
                    "linux-gnu* | linux-ohos* | linux-dietlibc* | linux-uclibc*",
                ),
                (
                    "-linux-musl* | -linux-uclibc*",
                    "-linux-musl* | -linux-ohos* | -linux-uclibc*",
                ),
                (
                    "-linux-gnu* | -linux-uclibc*",
                    "-linux-gnu* | -linux-ohos* | -linux-uclibc*",
                ),
                (
                    "-linux-gnu* | -linux-dietlibc* | -linux-uclibc*",
                    "-linux-gnu* | -linux-ohos* | -linux-dietlibc* | -linux-uclibc*",
                ),
            )
            for old, new in replacements:
                if old in contents:
                    contents = contents.replace(old, new, 1)

            linux_case = "\t-linux*)\n\t\tos="
            if "-linux-ohos*)" not in contents and linux_case in contents:
                contents = contents.replace(
                    linux_case,
                    "\t-linux-ohos*)\n\t\t;;\n" + linux_case,
                    1,
                )

            if contents == original_contents:
                self.output.warning(f"Could not patch OHOS support into {path}")
            else:
                save(self, path, contents)

    def build(self):
        self._patch_config_scripts()
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
