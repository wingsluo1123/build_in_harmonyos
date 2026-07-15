#!/usr/bin/env python3
"""Conan recipe for pass-otp 1.2.0 — pure Shell (Bash) script extension.

pass-otp is a pass extension for managing OTP (One-Time Password) tokens.
It is a pure shell script project with no compilation step; "installation"
consists of running make install to copy otp.bash to the extensions directory.

R32: settings.os not restricted (pure script, runs on any Unix-like OS).
R28: test_package/ exists.
R38: commands.json declared at software level (tool type).
"""
import os
import stat

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PassotpConan(ConanFile):
    name = "pass-otp"
    version = "1.2.0"
    description = "pass extension for managing OTP (One-Time Password) tokens"
    license = "GPL-3.0"
    homepage = "https://github.com/tadfisher/pass-otp"
    url = "https://github.com/tadfisher/pass-otp"

    package_type = "application"
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # pass-otp is a pure shell script; make install copies files to staging
        staging = os.path.join(self.source_folder, "pkg-staging")
        self.run(
            f'make install '
            f'PREFIX=/usr '
            f'DESTDIR="{staging}"',
            cwd=self.source_folder
        )

    def package(self):
        staging = os.path.join(self.source_folder, "pkg-staging")
        copy(self, "*", src=staging, dst=self.package_folder)
        # Ensure otp.bash is executable
        ext_path = os.path.join(self.package_folder, "usr", "lib", "password-store", "extensions", "otp.bash")
        if os.path.isfile(ext_path):
            os.chmod(ext_path, os.stat(ext_path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    def package_info(self):
        # pass-otp installs scripts to lib/password-store/extensions/
        # No binaries in bin/, no libraries — it's a pass extension
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
