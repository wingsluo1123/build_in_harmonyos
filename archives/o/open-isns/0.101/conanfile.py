#!/usr/bin/env python3
"""Conan recipe for open-isns 0.101."""
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
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class OpenIsnsConan(ConanFile):
    name = "open-isns"
    version = "0.101"
    description = "iSNS server, client tools, and development library"
    license = "LGPL-2.1-only"
    homepage = "https://github.com/open-iscsi/open-isns"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    win_bash = True

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("open-isns supports POSIX platforms")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        basic_layout(self)

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(
            [
                "--without-security",
                "--without-slp",
                "--disable-shared",
                "--enable-static",
                "--with-rundir=/data/local/tmp/open-isns",
            ]
        )
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os == "OHOS":
            config_sub = os.path.join(self.source_folder, "aclocal", "config.sub")
            replace_in_file(
                self,
                config_sub,
                "| arc | arm | arm[bl]e",
                "| aarch64 | arc | arm | arm[bl]e",
            )
            replace_in_file(
                self,
                config_sub,
                "| alphapca5[67]-* | alpha64pca5[67]-* | arc-*",
                "| alphapca5[67]-* | alpha64pca5[67]-* | aarch64-* | arc-*",
            )
            replace_in_file(
                self,
                config_sub,
                "linux-gnu* | linux-dietlibc | linux-uclibc*",
                "linux-gnu* | linux-ohos* | linux-dietlibc | linux-uclibc*",
            )
            replace_in_file(
                self,
                config_sub,
                "-mingw32* | -linux-gnu* | -linux-uclibc*",
                "-mingw32* | -linux-gnu* | -linux-ohos* | -linux-uclibc*",
            )
            replace_in_file(
                self,
                config_sub,
                "\t-linux*)\n\t\tos=`echo $os | sed -e 's|linux|linux-gnu|'`",
                "\t-linux-ohos*)\n\t\t;;\n"
                "\t-linux*)\n\t\tos=`echo $os | sed -e 's|linux|linux-gnu|'`",
            )
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(target="libisns.a", args=["-j1"])

    def package(self):
        copy(
            self,
            "libisns.a",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "lib"),
            keep_path=False,
        )
        copy(
            self,
            "*.h",
            src=os.path.join(self.source_folder, "include", "libisns"),
            dst=os.path.join(self.package_folder, "include", "libisns"),
            keep_path=False,
        )
        copy(
            self,
            "paths.h",
            src=os.path.join(self.build_folder, "include", "libisns"),
            dst=os.path.join(self.package_folder, "include", "libisns"),
            keep_path=False,
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = collect_libs(self) or ["isns"]
        self.cpp_info.set_property("cmake_file_name", "open-isns")
        self.cpp_info.set_property("cmake_target_name", "open-isns::open-isns")
        self.cpp_info.system_libs = ["pthread"]
