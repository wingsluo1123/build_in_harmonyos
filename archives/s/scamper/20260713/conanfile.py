#!/usr/bin/env python3
"""Conan recipe for scamper 20260713."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class ScamperConan(ConanFile):
    name = "scamper"
    version = "20260713"
    description = "Parallel Internet measurement utility"
    license = "GPL-2.0-only"
    homepage = "https://www.caida.org/catalog/software/scamper"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("scamper requires POSIX networking APIs")

    def requirements(self):
        self.requires("bzip2/1.0.8")
        self.requires("openssl/3.5.6")
        self.requires("pcre2/10.45")
        self.requires("xz/5.6.2")
        self.requires("zlib/1.3.1")

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
                "--disable-debug",
                "--disable-debug-file",
                "--disable-tests",
                "--disable-scamper-privsep",
                "--disable-scamper-ring",
                "--enable-scamper-select",
                "--enable-libs",
                "--enable-utils",
                "--enable-threads",
                "--with-pcre2=yes",
                "--with-zlib=yes",
                "--with-bz2=yes",
                "--with-lzma=yes",
            ]
        )
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        Autotools(self).install()
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
