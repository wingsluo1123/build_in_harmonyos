#!/usr/bin/env python3
"""Conan recipe for NSD 4.15.0."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import (
    Autotools,
    AutotoolsDeps,
    AutotoolsToolchain,
    PkgConfigDeps,
)
from conan.tools.layout import basic_layout


class NsdConan(ConanFile):
    name = "nsd"
    version = "4.15.0"
    description = "Authoritative-only DNS server"
    license = "BSD-3-Clause"
    homepage = "https://www.nlnetlabs.nl/projects/nsd/"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("nsd supports POSIX platforms")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires(
            "openssl/3.5.6@ohpcd/stable",
            transitive_headers=True,
            transitive_libs=True,
        )

    def _patch_config_sub(self, path):
        replace_in_file(
            self,
            path,
            "gnu* | android* | bsd*",
            "gnu* | android* | ohos* | bsd*",
        )
        replace_in_file(
            self,
            path,
            "linux-gnu* | linux-dietlibc* | linux-android*",
            "linux-gnu* | linux-ohos* | linux-dietlibc* | linux-android*",
        )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        if self.settings.os == "OHOS":
            self._patch_config_sub(os.path.join(self.source_folder, "config.sub"))
            self._patch_config_sub(
                os.path.join(self.source_folder, "simdzone", "config.sub")
            )

    def layout(self):
        basic_layout(self)

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        openssl = self.dependencies["openssl"].package_folder
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(
            [
                f"--with-ssl={openssl}",
                "--with-libevent=no",
                "--disable-dnstap",
                "--disable-systemd",
                "--disable-xdp",
                "--disable-westmere",
                "--disable-haswell",
                "--disable-recvmmsg",
                "--disable-tcp-fastopen",
                "--with-configdir=/etc/nsd",
                "--with-dbdir=/data/local/tmp/nsd/db",
                "--with-pidfile=/data/local/tmp/nsd/nsd.pid",
                "--with-xfrdir=/data/local/tmp/nsd/xfr",
            ]
        )
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        Autotools(self).install()

    def package_info(self):
        self.cpp_info.bindirs = ["sbin", "bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.buildenv_info.append_path(
            "PATH", os.path.join(self.package_folder, "sbin")
        )
        self.runenv_info.append_path(
            "PATH", os.path.join(self.package_folder, "sbin")
        )
