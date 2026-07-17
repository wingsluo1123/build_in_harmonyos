#!/usr/bin/env python3
"""Conan recipe for ncmpcpp 0.10.1-r2."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class NcmpcppConan(ConanFile):
    name = "ncmpcpp"
    version = "0.10.1-r2"
    description = "Feature-rich ncurses client for Music Player Daemon"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/ncmpcpp/ncmpcpp"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("ncmpcpp requires POSIX and ncurses APIs")

    def requirements(self):
        self.requires("boost/1.84.0")
        self.requires("fftw/3.3.10")
        self.requires("icu4c/78")
        self.requires("libmpdclient/2.23")
        self.requires("ncurses/6.5")
        self.requires("readline/8.3")
        self.requires("taglib/2.3")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--host=aarch64-unknown-linux-gnu",
                "--disable-shared",
                "--enable-static",
                "--enable-clock",
                "--enable-outputs",
                "--enable-visualizer",
                "--with-fftw=yes",
                "--with-taglib=yes",
                "--with-lto=no",
            ]
        )
        tc.generate()

    def build(self):
        self.run("autoreconf -fi", cwd=self.source_folder)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        Autotools(self).install()
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
