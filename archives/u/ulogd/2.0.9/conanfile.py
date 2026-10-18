#!/usr/bin/env python3
"""Conan recipe - ulogd 2.0.9 (Autotools).

ulogd: Userspace logging daemon for netfilter/iptables. Built natively
for HarmonyOS PC (aarch64-unknown-linux-ohos).

Adaptation notes:
- E007: config.sub patched to recognize __OHOS__/HarmonyOS
- E011/E114: HMDFS umask 077 temp-dir fix applied in-recipe
- nfct/nfacct modules disabled (libnetfilter_conntrack and libnetfilter_acct
  not yet published on ohpcd); nflog module enabled with available deps
- PKG_CHECK_MODULES deps resolved via PkgConfigDeps
"""
import glob
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class UlogdConan(ConanFile):
    name = "ulogd"
    version = "2.0.9"
    description = "Userspace logging daemon for netfilter/iptables"
    license = "GPL-2.0-or-later"
    homepage = "https://netfilter.org/projects/ulogd/"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ulogd supports Linux and OHOS targets, got {self.settings.os}"
            )

    def requirements(self):
        self.requires("libnfnetlink/1.0.2")
        self.requires("libnetfilter_log/1.0.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
            tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
            tc.extra_cflags.append("-D_UAPI_LINUX_SOCKET_H")
            tc.extra_cflags.append("-D__kernel_sa_family_t=uint16_t")
            tc.extra_cflags.append("-D_UAPI_NFNETLINK_H")
        tc.configure_args.append("--disable-nfct")
        tc.configure_args.append("--disable-nfacct")
        tc.configure_args.append("--disable-pgsql")
        tc.configure_args.append("--disable-mysql")
        tc.configure_args.append("--disable-sqlite3")
        tc.configure_args.append("--disable-dbi")
        tc.configure_args.append("--disable-pcap")
        tc.configure_args.append("--disable-json")
        tc.generate()
        PkgConfigDeps(self).generate()
        self._clean_dependency_la_files()

    def _clean_dependency_la_files(self):
        for _ref, _d in self.dependencies.items():
            for la in glob.glob(os.path.join(_d.package_folder, "lib", "**", "*.la"), recursive=True):
                os.remove(la)

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os == "OHOS":
            configure_script = os.path.join(self.source_folder, "configure")
            self._make_config_status_tmp_writable(configure_script)
            command = (
                "CONFIG_SHELL=/bin/sh SHELL=/bin/sh "
                + shlex.join(["/bin/sh", configure_script])
            )
            autotools = Autotools(self)
            if autotools._configure_args:
                command = f"{command} {autotools._configure_args}"
            self.run(command, cwd=self.build_folder)
            autotools.make(args=["-j1"])
        else:
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j1"])

    @staticmethod
    def _make_config_status_tmp_writable(path):
        with open(path, "r", encoding="utf-8") as handle:
            content = handle.read()
        patched = content.replace(
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
            'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`',
        ).replace(
            '(umask 077 && mkdir "$tmp")',
            'mkdir "$tmp"',
        )
        if patched != content:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(patched)

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        sbindir = os.path.join(self.package_folder, "sbin")
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(sbindir):
            os.makedirs(bindir, exist_ok=True)
            for name in os.listdir(sbindir):
                shutil.move(os.path.join(sbindir, name), bindir)
            os.rmdir(sbindir)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
