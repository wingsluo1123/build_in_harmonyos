#!/usr/bin/env python3
"""Conan recipe for sipsak 0.9.7 on HarmonyOS."""

import os

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class SipsakConan(ConanFile):
    name = "sipsak"
    version = "0.9.7"
    description = "SIP stress and diagnostics command-line utility"
    license = "GPL-2.0-or-later"
    homepage = "https://sipsak.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def build(self):
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
        build_type_flags = {
            "Debug": "-g -O0",
            "Release": "-O2 -DNDEBUG",
            "MinSizeRel": "-Os -DNDEBUG",
            "RelWithDebInfo": "-O2 -g -DNDEBUG",
        }[str(self.settings.build_type)]
        flags = (
            build_type_flags + " "
            "-DPACKAGE_NAME=\\\"sipsak\\\" "
            "-DPACKAGE_BUGREPORT=\\\"nils@sipsak.org\\\" "
            "-DDEFAULT_TIMEOUT=500 "
            "-fcommon -D_GNU_SOURCE -DPACKAGE_VERSION=\\\"0.9.7\\\" "
            "-DHAVE_STDIO_H -DHAVE_STDLIB_H -DHAVE_STDARG_H "
            "-DHAVE_STDINT_H -DHAVE_STRING_H -DHAVE_STRINGS_H "
            "-DHAVE_CTYPE_H -DHAVE_ERRNO_H -DHAVE_UNISTD_H "
            "-DHAVE_SYS_TYPES_H -DHAVE_SYS_TIME_H -DHAVE_SYS_PARAM_H "
            "-DHAVE_SYS_SOCKET_H -DHAVE_SYS_UTSNAME_H -DHAVE_SYS_POLL_H "
            "-DHAVE_NETDB_H -DHAVE_NETINET_IN_H -DHAVE_ARPA_INET_H "
            "-DHAVE_REGEX_H -DHAVE_SIGNAL_H -DHAVE_LIMITS_H "
            "-DHAVE_SYSLOG_H -DHAVE_SYS_WAIT_H "
            "-DHAVE_GETOPT_H -DHAVE_GETOPT_LONG -DHAVE_INET_NTOP "
            "-DHAVE_STRNCASECMP -DHAVE_STRCASESTR -DHAVE_CALLOC "
            "-DHAVE_GETDOMAINNAME -DTIME_WITH_SYS_TIME"
        )
        output = os.path.join(self.build_folder, "sipsak")
        self.run(
            '"{}" {} -I"{}" {} -o "{}"'.format(
                cc, flags, os.path.join(self.source_folder, "src"), source_args, output
            ),
            env="conanbuild",
        )
        self._run_upstream_tests(cc, build_type_flags)

    def _run_upstream_tests(self, cc, build_type_flags):
        """Compile and run the upstream Check-based unit tests when the Check
        framework is present in the build environment (e.g. the OHOS device)."""
        check_prefix = self._find_check_prefix()
        if not check_prefix:
            self.output.info(
                "Check framework not found; skipping upstream tests"
            )
            return
        source_folder = self.source_folder
        # The upstream tests include "../config.h", which autoconf normally
        # generates. Emit a minimal OHOS-compatible config header.
        config_h = os.path.join(source_folder, "config.h")
        if not os.path.isfile(config_h):
            with open(config_h, "w", encoding="utf-8") as handle:
                handle.write(
                    "#define HAVE_CHECK_H 1\n"
                    "#define HAVE_STDIO_H 1\n"
                    "#define HAVE_STDLIB_H 1\n"
                    "#define HAVE_STRING_H 1\n"
                    "#define HAVE_STRINGS_H 1\n"
                    "#define HAVE_UNISTD_H 1\n"
                )
        test_flags = (
            build_type_flags
            + " -fcommon -D_GNU_SOURCE -DRUNNING_CHECK -DHAVE_CHECK_H "
            + '-I"{src}" -I"{src}/src" -I"{prefix}/include" '.format(
                src=source_folder, prefix=check_prefix
            )
        )
        tests = (
            (
                "check_helper",
                [
                    os.path.join(source_folder, "tests", "check_helper.c"),
                    os.path.join(source_folder, "src", "helper.c"),
                    os.path.join(source_folder, "src", "exit_code.c"),
                ],
            ),
            (
                "check_md5",
                [
                    os.path.join(source_folder, "tests", "check_md5.c"),
                    os.path.join(source_folder, "src", "md5.c"),
                ],
            ),
        )
        for name, test_sources in tests:
            source_args = " ".join('"{}"'.format(item) for item in test_sources)
            binary = os.path.join(self.build_folder, name)
            self.run(
                '"{}" {} {} -L"{prefix}/lib" -lcheck -o "{}"'.format(
                    cc, test_flags, source_args, binary, prefix=check_prefix
                ),
                env="conanbuild",
            )
            self.run('"{}"'.format(binary), env="conanbuild")

    def _find_check_prefix(self):
        """Locate the Check framework without hardcoding a developer path.

        Honor the CHECK_PREFIX environment variable, ask pkg-config when
        available, then probe the conventional /usr/local prefixes.
        """
        candidates = []
        env_prefix = os.environ.get("CHECK_PREFIX")
        if env_prefix:
            candidates.append(env_prefix)
        try:
            import subprocess

            output = subprocess.check_output(
                ["pkg-config", "--variable=prefix", "check"],
                stderr=subprocess.STDOUT,
                timeout=20,
            ).decode("utf-8", errors="replace").strip()
            if output:
                candidates.append(output)
        except Exception:
            pass
        candidates.append("/usr/local")
        candidates.append("/storage/Users/currentUser/usr/local")
        for prefix in candidates:
            if os.path.isfile(os.path.join(prefix, "include", "check.h")):
                return prefix
        return None

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
