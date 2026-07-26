#!/usr/bin/env python3
"""Conan recipe for OpenSSL 1.1.1w on Linux and HarmonyOS/OHOS."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class OpensslConan(ConanFile):
    name = "openssl"
    version = "1.1.1w"
    description = "Industry-standard TLS/SSL and cryptographic library"
    license = "Apache-2.0"
    homepage = "https://www.openssl.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/main/archives/o/openssl/1.1.1w"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [False],
    }
    default_options = {
        "shared": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # OpenSSL is built without zlib support so the package is self-contained.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_executables(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", os.environ.get("CC", "clang"))
        tool_dir = os.path.dirname(cc) if os.path.isabs(cc) else ""
        ar = compilers.get("ar") or (os.path.join(tool_dir, "llvm-ar") if tool_dir else "llvm-ar")
        ranlib = compilers.get("ranlib") or (
            os.path.join(tool_dir, "llvm-ranlib") if tool_dir else "llvm-ranlib"
        )
        return (
            cc,
            compilers.get("cpp", os.environ.get("CXX", "clang++")),
            ar,
            ranlib,
        )

    def build(self):
        apply_conandata_patches(self)

        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"OpenSSL 1.1.1w is only supported on Linux and OHOS, got {self.settings.os}"
            )

        cc, cxx, ar, ranlib = self._compiler_executables()
        perl = os.environ.get("PERL", "perl")
        prefix = self.package_folder
        openssldir = os.path.join(prefix, "ssl")
        configure = (
            f'CC="{cc}" CXX="{cxx}" AR="{ar}" RANLIB="{ranlib}" '
            'CFLAGS="-fPIC -O2 -D__OHOS__" '
            f'{perl} ./Configure openharmony-aarch64 '
            f'--prefix="{prefix}" --openssldir="{openssldir}" '
            "no-asm no-shared"
        )
        self.run(configure, cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # install_sw omits the documentation test suite and installs into prefix.
        self.run("make install_sw", cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["ssl", "crypto"]
        self.cpp_info.system_libs = ["dl", "pthread"]
