#!/usr/bin/env python3
"""Conan recipe for Cyrus SASL 2.1.28, the libsasl2 authentication framework."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import collect_libs, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CyrusSaslConan(ConanFile):
    name = "cyrus-sasl"
    version = "2.1.28"
    description = "SASL authentication framework and libsasl2 library"
    license = "BSD-Attribution-HPND-disclaimer"
    homepage = "https://www.cyrusimap.org/sasl/"
    url = "https://github.com/cyrusimap/cyrus-sasl"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static", "--with-staticsasl"])
        tc.configure_args.extend([
            "--disable-sample",
            "--disable-staticdlopen",
            "--disable-alwaystrue",
            "--disable-auth-sasldb",
            "--disable-gssapi",
            "--disable-httpform",
            "--disable-krb4",
            "--disable-ldapdb",
            "--disable-login",
            "--disable-ntlm",
            "--disable-otp",
            "--disable-passdss",
            "--disable-sia",
            "--disable-sql",
            "--disable-srp",
            "--disable-srp-setpass",
            "--with-dblib=none",
            "--without-authdaemond",
            "--without-des",
            "--without-gdbm",
            "--without-ldap",
            "--without-mysql",
            "--without-openssl",
            "--without-opie",
            "--without-pam",
            "--without-pgsql",
            "--without-pwcheck",
            "--without-saslauthd",
            "--without-sqlite",
            "--without-sqlite3",
        ])
        tc.generate()

    def build(self):
        self._patch_configure_for_ohos()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        libs = collect_libs(self)
        self.cpp_info.libs = libs or ["sasl2"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "cyrus-sasl")
        self.cpp_info.set_property("cmake_target_name", "cyrus-sasl::cyrus-sasl")
        self.cpp_info.set_property("pkg_config_name", "libsasl2")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]

    def _patch_configure_for_ohos(self):
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure):
            return
        with open(configure, encoding="utf-8", errors="ignore") as source:
            content = source.read()
        replacements = {
            "umask 077": "umask 022",
            "${TMPDIR-/tmp}": "${TMPDIR:-${HOME}/tmp}",
            "${TMPDIR:-/tmp}": "${TMPDIR:-${HOME}/tmp}",
        }
        for needle, replacement in replacements.items():
            if needle not in content:
                raise ConanInvalidConfiguration(
                    f"Expected configure pattern not found: {needle}"
                )
            content = content.replace(needle, replacement)
        with open(configure, "w", encoding="utf-8") as target:
            target.write(content)
