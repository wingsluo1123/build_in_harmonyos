#!/usr/bin/env python3
"""Conan recipe - zabbix 7.4.5 (Autotools: configure + make).

Enterprise-class open source monitoring solution.
This recipe builds zabbix agent, get, and sender for HarmonyOS PC arm64.

Dependencies:
  - openssl/3.5.6.1.1  (TLS support)
  - pcre2/10.45         (regular expression support)
  - zlib/1.3.1          (compression support)

R26: Not a system same-name library - dynamic linking is OK.
R32: settings.os must check in ("Linux", "OHOS").

Patches:
  0001-dns-disable-_res-for-ohos.patch  - Disable _res global variable on OHOS
  configure umask fix                  - Inline replacement in build() (HMDFS)
"""

import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    get, apply_conandata_patches, export_conandata_patches,
    load, save,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class ZabbixConan(ConanFile):
    name = "zabbix"
    version = "7.4.5"
    description = "Enterprise-class open source monitoring solution"
    license = "AGPL-3.0"
    homepage = "https://www.zabbix.com"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6.1.1")
        self.requires("pcre2/10.45")
        self.requires("zlib/1.3.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "zabbix is only supported on Linux/OHOS, not "
                + str(self.settings.os)
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
        # Fix out-of-source build: DEFAULT_INCLUDES lacks -I$(top_builddir)
        # causing "config.h not found" because it's generated in build dir.
        # This is a generated file fix (configure), not in source tarball,
        # so we handle it inline rather than via patch.
        configure_path = os.path.join(self.source_folder, "configure")
        content = load(self, configure_path)
        content = content.replace(
            "DEFAULT_INCLUDES='-I$(top_srcdir)/include/common -I$(top_srcdir)/include'",
            "DEFAULT_INCLUDES='-I$(top_builddir)/include/common -I$(top_srcdir)/include/common -I$(top_srcdir)/include'",
        )
        save(self, configure_path, content)

    def generate(self):
        # Generate corrected pkg-config files for dependencies
        pkgdeps = PkgConfigDeps(self)
        pkgdeps.generate()

        tc = AutotoolsToolchain(self)
        openssl_root = self.dependencies["openssl"].package_folder
        pcre2_root = self.dependencies["pcre2"].package_folder
        zlib_root = self.dependencies["zlib"].package_folder

        # Fix: create libpcre2-8.pc (zabbix checks for libpcre2-8, not pcre2)
        # PkgConfigDeps only generates pcre2.pc
        gen_dir = os.path.join(self.build_folder, "build-release", "conan")
        os.makedirs(gen_dir, exist_ok=True)
        libpcre2_pc = os.path.join(gen_dir, "libpcre2-8.pc")
        save(self, libpcre2_pc,
            "prefix=" + pcre2_root + "\n"
            "libdir=${prefix}/lib\n"
            "includedir=${prefix}/include\n\n"
            "Name: libpcre2-8\n"
            "Description: PCRE2 - Perl compatible regular expressions C library\n"
            "Version: 10.45\n"
            "Libs: -L${libdir} -lpcre2-8\n"
            "Cflags: -I${includedir}\n"
        )

        tc.configure_args.extend([
            "--build=aarch64-linux-gnu",
            "--host=aarch64-linux-gnu",
            "--enable-agent",
            "--disable-server",
            "--disable-proxy",
            "--disable-agent2",
            "--disable-java",
            "--disable-webservice",
            "--without-mysql",
            "--without-postgresql",
            "--without-sqlite3",
            "--without-libxml2",
            "--without-unixodbc",
            "--without-net-snmp",
            "--without-ssh2",
            "--without-ssh",
            "--without-openipmi",
            "--without-ares",
            "--without-libevent",
            "--without-gnutls",
            "--without-libmodbus",
            "--without-ldap",
            "--without-libcurl",
            "--without-iconv",
            "--with-openssl=" + openssl_root,
            "--with-libpcre2=" + pcre2_root,
            "--with-zlib=" + zlib_root,
        ])
        tc.generate()

    def build(self):
        # HMDFS /tmp is read-only, use writable TMPDIR for config.guess
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        old_tmp = os.environ.get("TMPDIR", "")
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir

        # Fix pcre2 conan package: its .pc has prefix=/ causing -I//include
        pcre2_root = self.dependencies["pcre2"].package_folder
        pcre2_pc = os.path.join(pcre2_root, "lib", "pkgconfig", "libpcre2-8.pc")
        orig_pc = load(self, pcre2_pc)
        # Only fix if prefix is literally "/" (not already fixed)
        import re
        fixed_pc = re.sub(
            r'^prefix=/$',
            'prefix=' + pcre2_root,
            orig_pc,
            count=1,
            flags=re.MULTILINE,
        )
        save(self, pcre2_pc, fixed_pc)

        try:
            # Prevent make from regenerating autotools files (not available)
            os.environ["ACLOCAL"] = "true"
            os.environ["AUTOCONF"] = "true"
            os.environ["AUTOHEADER"] = "true"
            os.environ["AUTOMAKE"] = "true"
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j2"])
        finally:
            if old_tmp:
                os.environ["TMPDIR"] = old_tmp
            else:
                os.environ.pop("TMPDIR", None)
            os.environ.pop("TMP", None)
            for v in ["ACLOCAL", "AUTOCONF", "AUTOHEADER", "AUTOMAKE"]:
                os.environ.pop(v, None)
            os.environ.pop("LIBPCRE2_CFLAGS", None)
            os.environ.pop("LIBPCRE2_LIBS", None)

    def package(self):
        # Fix out-of-source build: install-data-hook uses relative path
        # "../../conf/" which points to wrong location in out-of-source build.
        # Replace with absolute source path.
        agent_mf = os.path.join(self.build_folder, "src", "zabbix_agent", "Makefile")
        if os.path.exists(agent_mf):
            mf_content = load(self, agent_mf)
            mf_content = mf_content.replace(
                'cp "../../conf/',
                'cp "' + os.path.join(self.source_folder, "conf") + '/'
            )
            save(self, agent_mf, mf_content)

        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["sbin", "bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "sbin")
        )
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
