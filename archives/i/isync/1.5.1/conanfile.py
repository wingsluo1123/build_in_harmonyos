#!/usr/bin/env python3
"""Conan recipe for isync 1.5.1 — Autotools build system.

isync (mbsync) is an IMAP and MailDir mailbox synchronizer.
Build: ./configure --with-ssl=... --with-zlib=... && make -j1
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class IsyncConan(ConanFile):
    name = "isync"
    version = "1.5.1"
    description = "IMAP and MailDir mailbox synchronizer (mbsync)"
    license = "GPL-2.0-or-later"
    homepage = "https://isync.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/1.1.1w")
        self.requires("zlib/1.3.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("isync is only supported on Linux/OHOS")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Use Conan-managed dependency paths for SSL and zlib
        openssl_prefix = self.dependencies["openssl"].package_folder
        zlib_prefix = self.dependencies["zlib"].package_folder
        tc.configure_args.append("--with-ssl=" + openssl_prefix)
        tc.configure_args.append("--with-zlib=" + zlib_prefix)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E129: HMDFS setgid fix — replace umask 077 with 022 in configure
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure_path):
            with open(configure_path, "r") as fh:
                content = fh.read()
            content = content.replace("umask 077", "umask 022")
            with open(configure_path, "w") as fh:
                fh.write(content)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
