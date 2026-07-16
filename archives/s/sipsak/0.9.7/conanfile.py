#!/usr/bin/env python3
"""Conan recipe for sipsak 0.9.7 on HarmonyOS."""

import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class SipsakConan(ConanFile):
    name = "sipsak"
    version = "0.9.7"
    description = "SIP stress and diagnostics command-line utility"
    license = "GPL-2.0-or-later"
    homepage = "https://sipsak.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")
        sources = (
            "transport.c auth.c header_f.c helper.c md5.c request.c "
            "shoot.c sipsak.c exit_code.c"
        )
        source_args = " ".join(
            '"{}"'.format(os.path.join(self.source_folder, "src", item))
            for item in sources.split()
        )
        flags = (
            "-O2 -D_GNU_SOURCE -DPACKAGE_VERSION=\\\"0.9.7\\\" "
            "-DHAVE_STDIO_H -DHAVE_STDLIB_H -DHAVE_STDARG_H "
            "-DHAVE_STDINT_H -DHAVE_STRING_H -DHAVE_STRINGS_H "
            "-DHAVE_CTYPE_H -DHAVE_ERRNO_H -DHAVE_UNISTD_H "
            "-DHAVE_SYS_TYPES_H -DHAVE_SYS_TIME_H -DHAVE_SYS_PARAM_H "
            "-DHAVE_SYS_SOCKET_H -DHAVE_SYS_UTSNAME_H -DHAVE_SYS_POLL_H "
            "-DHAVE_NETDB_H -DHAVE_NETINET_IN_H -DHAVE_ARPA_INET_H "
            "-DHAVE_REGEX_H -DHAVE_SIGNAL_H -DHAVE_LIMITS_H "
            "-DHAVE_GETOPT_H -DHAVE_GETOPT_LONG -DHAVE_INET_NTOP "
            "-DHAVE_STRNCASECMP -DHAVE_STRCASESTR -DHAVE_CALLOC "
            "-DHAVE_GETDOMAINNAME -DTIME_WITH_SYS_TIME"
        )
        output = os.path.join(self.build_folder, "sipsak")
        self.run(
            '"{}" {} -I"{}" {} -o "{}"'.format(
                cc, flags, os.path.join(self.source_folder, "src"), source_args, output
            )
        )

    def package(self):
        copy(
            self,
            "sipsak",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "bin"),
        )
        copy(
            self,
            "sipsak.1",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
