#!/usr/bin/env python3
"""Conan recipe for NSD 4.15.0."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import (
    get,
    load,
    replace_in_file,
)
from conan.tools.gnu import (
    Autotools,
    AutotoolsDeps,
    AutotoolsToolchain,
    PkgConfigDeps,
)
from conan.tools.layout import basic_layout
from conan.tools.microsoft import unix_path


class NsdConan(ConanFile):
    name = "nsd"
    version = "4.15.0"
    description = "Authoritative-only DNS server"
    license = "BSD-3-Clause"
    homepage = "https://www.nlnetlabs.nl/projects/nsd/"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    win_bash = True

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("nsd supports POSIX platforms")

    def requirements(self):
        self.requires(
            "openssl/3.5.6",
            transitive_headers=True,
            transitive_libs=True,
        )

    def _patch_config_sub(self, path):
        contents = load(self, path)
        if "ohos* | bsd*" not in contents:
            replace_in_file(
                self,
                path,
                "gnu* | android* | bsd*",
                "gnu* | android* | ohos* | bsd*",
            )
        if "linux-ohos*" not in contents:
            replace_in_file(
                self,
                path,
                "linux-gnu* | linux-dietlibc* | linux-android*",
                "linux-gnu* | linux-ohos* | linux-dietlibc* | linux-android*",
            )

    def _patch_config_status_tempdir(self, path):
        contents = load(self, path)
        if 'mktemp -d "${TMPDIR:-.}/confXXXXXX"' not in contents:
            replace_in_file(
                self,
                path,
                'mktemp -d "./confXXXXXX"',
                'mktemp -d "${TMPDIR:-.}/confXXXXXX"',
            )
        if 'tmp="${TMPDIR:-.}/conf$$-$RANDOM"' not in contents:
            replace_in_file(
                self,
                path,
                "tmp=./conf$$-$RANDOM",
                'tmp="${TMPDIR:-.}/conf$$-$RANDOM"',
            )
        if "(umask 022 && mktemp -d" not in contents:
            replace_in_file(
                self,
                path,
                "(umask 077 && mktemp -d",
                "(umask 022 && mktemp -d",
            )
        if '(umask 022 && mkdir "$tmp")' not in contents:
            replace_in_file(
                self,
                path,
                '(umask 077 && mkdir "$tmp")',
                '(umask 022 && mkdir "$tmp")',
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        basic_layout(self)

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        openssl = unix_path(
            self, self.dependencies["openssl"].package_folder
        )
        toolchain = AutotoolsToolchain(self)
        if self.settings.os == "OHOS" and not cross_building(self):
            # Native OHOS workers cannot always execute config.guess because
            # its temporary directory may be read-only.  Supplying the
            # canonical tuple avoids that probe while preserving native mode.
            toolchain.configure_args.extend(
                [
                    "--build=aarch64-unknown-linux-ohos",
                    "--host=aarch64-unknown-linux-ohos",
                ]
            )
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
            ]
        )
        if self.settings.os == "OHOS":
            toolchain.configure_args.extend(
                [
                    "--with-dbdir=/data/local/tmp/nsd/db",
                    "--with-pidfile=/data/local/tmp/nsd/nsd.pid",
                    "--with-xfrdir=/data/local/tmp/nsd/xfr",
                ]
            )
        toolchain.generate()

    def build(self):
        if self.settings.os == "OHOS":
            self._patch_config_sub(os.path.join(self.source_folder, "config.sub"))
            self._patch_config_sub(
                os.path.join(self.source_folder, "simdzone", "config.sub")
            )
            if not cross_building(self):
                # HMDFS cannot use Autoconf's 077 temporary mode reliably.
                # Apply the repository's E011-compatible 022 mode.
                self._patch_config_status_tempdir(
                    os.path.join(self.source_folder, "configure")
                )
                self._patch_config_status_tempdir(
                    os.path.join(self.source_folder, "simdzone", "configure")
                )
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
