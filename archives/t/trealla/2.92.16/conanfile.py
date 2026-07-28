#!/usr/bin/env python3
"""Conan recipe for Trealla Prolog 2.92.16."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    chdir,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class TreallaConan(ConanFile):
    name = "trealla"
    version = "2.92.16"
    description = "Compact, efficient Prolog interpreter"
    license = "MIT"
    homepage = "https://github.com/trealla-prolog/trealla"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("trealla supports POSIX platforms")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        basic_layout(self)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        with chdir(self, self.source_folder):
            self.run(
                "make -j1 "
                "ISOCLINE=1 NOFFI=1 NOSSL=1 EMBED=1 "
                f'GIT_VERSION="v{self.version}" release',
                env="conanbuild",
            )

    def package(self):
        copy(
            self,
            "tpl",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "tests"),
            dst=os.path.join(
                self.package_folder, "share", "trealla", "upstream-tests", "tests"
            ),
            keep_path=True,
        )
        copy(
            self,
            "tpl",
            src=self.source_folder,
            dst=os.path.join(
                self.package_folder, "share", "trealla", "upstream-tests"
            ),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.buildenv_info.append_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
        self.runenv_info.append_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
