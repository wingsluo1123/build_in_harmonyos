#!/usr/bin/env python3
"""Conan recipe for libp11 0.4.16-r0."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class Libp11Conan(ConanFile):
    name = "libp11"
    version = "0.4.16-r0"
    description = "PKCS#11 wrapper library for OpenSSL applications"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/OpenSC/libp11"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libp11 supports Linux and OHOS")

    def requirements(self):
        self.requires("openssl/3.5.6")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--host=aarch64-unknown-linux-gnu",
            "--disable-shared",
            "--enable-static",
            "--disable-static-engine",
            "--disable-api-doc",
            "--with-enginesdir=/lib/engines-3",
            "--with-modulesdir=/lib/ossl-modules",
        ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self.run("./bootstrap", cwd=self.source_folder)
        autotools = Autotools(self)
        autotools.configure()
        self.run("make -C src -j1 libp11.la", cwd=self.source_folder)

    def package(self):
        src_dir = os.path.join(self.source_folder, "src")
        copy(self, "libp11.a", src=os.path.join(src_dir, ".libs"), dst=os.path.join(self.package_folder, "lib"))
        for header in ("libp11.h", "p11_err.h", "pkcs11.h"):
            copy(self, header, src=src_dir, dst=os.path.join(self.package_folder, "include"))
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["p11"]
        self.cpp_info.set_property("cmake_file_name", "libp11")
        self.cpp_info.set_property("cmake_target_name", "libp11::libp11")
        self.cpp_info.system_libs = ["dl", "pthread"]
