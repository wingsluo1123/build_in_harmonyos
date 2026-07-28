#!/usr/bin/env python3
"""Conan recipe for Cyrus SASL 2.1.28, the libsasl2 authentication framework."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get
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
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
            tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static", "--with-staticsasl"])
        tc.configure_args.extend([
            "--disable-dependency-tracking",
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
        if self.settings.os == "OHOS":
            self._patch_configure_for_ohos()
        autotools = Autotools(self)
        if self.settings.os == "OHOS":
            configure = os.path.join(self.source_folder, "configure")
            tmpdir = os.path.join(self.source_folder, "tmp")
            os.makedirs(tmpdir, exist_ok=True)
            build_cc = "/data/service/hnp/bin/clang"
            self.run(
                f'TMPDIR="{tmpdir}" CONFIG_SHELL=/system/bin/sh SHELL=/system/bin/sh '
                f'CC_FOR_BUILD="{build_cc}" CPP_FOR_BUILD="{build_cc} -E" '
                f'/system/bin/sh "{configure}" {autotools._configure_args}'
            )
        else:
            autotools.configure()
        if self.settings.os == "OHOS":
            self._copy_linksrcs_for_ohos()
            self._patch_makefile_for_ohos()
            self.run(f'TMPDIR="{tmpdir}" make -j1')
        else:
            autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        if self.settings.os == "OHOS":
            tmpdir = os.path.join(self.source_folder, "tmp")
            os.makedirs(tmpdir, exist_ok=True)
            self._patch_makefile_for_ohos()
            self.run(
                f'TMPDIR="{tmpdir}" make install '
                f'DESTDIR="{self.package_folder}" -j1'
            )
        else:
            autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["sasl2"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "cyrus-sasl")
        self.cpp_info.set_property("cmake_target_name", "cyrus-sasl::cyrus-sasl")
        self.cpp_info.set_property("pkg_config_name", "libsasl2")
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]

    def _patch_configure_for_ohos(self):
        folders = {
            self.source_folder,
            self.build_folder,
            os.getcwd(),
            os.path.dirname(self.build_folder),
        }
        for folder in folders:
            configure = os.path.join(folder, "configure")
            if not os.path.isfile(configure):
                continue
            with open(configure, encoding="utf-8", errors="ignore") as source:
                content = source.read()
            replacements = {
                "${TMPDIR-/tmp}": "${TMPDIR:-${HOME}/tmp}",
                "${TMPDIR:-/tmp}": "${TMPDIR:-${HOME}/tmp}",
            }
            if "umask 077" in content:
                content = content.replace("umask 077", "umask 022")
            elif "umask 022" not in content:
                raise ConanInvalidConfiguration(
                    "Expected configure pattern not found: umask 077"
                )
            for needle, replacement in replacements.items():
                if needle in content:
                    content = content.replace(needle, replacement)
            with open(configure, "w", encoding="utf-8") as target:
                target.write(content)
            os.chmod(configure, 0o755)
            config_dir = os.path.join(folder, "config")
            for script in ("install-sh", "missing"):
                script_path = os.path.join(config_dir, script)
                if os.path.isfile(script_path):
                    os.chmod(script_path, 0o755)

    def _copy_linksrcs_for_ohos(self):
        links = {
            "sasldb/db_none.c": "lib/db_none.c",
            "plugins/cram.c": "lib/cram.c",
            "plugins/digestmd5.c": "lib/digestmd5.c",
            "plugins/plain.c": "lib/plain.c",
            "plugins/anonymous.c": "lib/anonymous.c",
        }
        for source, target in links.items():
            shutil.copy2(
                os.path.join(self.source_folder, source),
                os.path.join(self.source_folder, target),
            )

    def _patch_makefile_for_ohos(self):
        for root, _, files in os.walk(self.source_folder):
            if "Makefile" not in files:
                continue
            makefile = os.path.join(root, "Makefile")
            with open(makefile, encoding="utf-8", errors="ignore") as source:
                content = source.read()
            content = content.replace("ln -s .libs/$@ $@", "cp -pR .libs/$@ $@")
            content = content.replace(
                "MKDIR_P = config/install-sh -c -d",
                "MKDIR_P = /system/bin/sh config/install-sh -c -d",
            )
            content = content.replace(
                "MKDIR_P = ../config/install-sh -c -d",
                "MKDIR_P = /system/bin/sh ../config/install-sh -c -d",
            )
            content = content.replace(
                "\n\t../config/install-sh",
                "\n\t/system/bin/sh ../config/install-sh",
            )
            content = content.replace(
                "\n\tconfig/install-sh",
                "\n\t/system/bin/sh config/install-sh",
            )
            with open(makefile, "w", encoding="utf-8") as target:
                target.write(content)
