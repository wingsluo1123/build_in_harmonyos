#!/usr/bin/env python3
"""Conan recipe for w_scan 20210218."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import (
    copy,
    get,
    replace_in_file,
)
from conan.tools.layout import basic_layout


class WScanConan(ConanFile):
    name = "w-scan"
    version = "20210218"
    description = "Command-line DVB channel scanner"
    license = "GPL-2.0-or-later"
    homepage = "https://wirbel.htpc-forum.de/w_scan/index2.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    _SOURCES = [
        "atsc_psip_section.c",
        "countries.c",
        "descriptors.c",
        "diseqc.c",
        "dump-dvbscan.c",
        "dump-vdr.c",
        "dump-xine.c",
        "dump-mplayer.c",
        "dump-vlc-m3u.c",
        "dump-xml.c",
        "dvbscan.c",
        "emulate.c",
        "iconv_codes.c",
        "char-coding.c",
        "lnb.c",
        "parse-dvbscan.c",
        "satellites.c",
        "scan.c",
        "section.c",
        "tools.c",
    ]

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def export_sources(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _get_cc(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return compilers.get("c") or "clang"

    def _compiler_is_clang(self):
        return "clang" in str(self.settings.compiler).lower()

    def build(self):
        # The upstream file uses CRLF; preserve it while making the include portable.
        replace_in_file(
            self,
            os.path.join(self.source_folder, "emulate.c"),
            "#include <sys/errno.h>\r\n",
            "#include <errno.h>\r\n",
        )

        # OHOS clang does not get time_t transitively from the DVB headers.
        replace_in_file(
            self,
            os.path.join(self.source_folder, "descriptors.h"),
            '#include "extended_frontend.h"',
            '#include <time.h>\n#include "extended_frontend.h"',
        )

        cc = self._get_cc()
        os.makedirs(self.build_folder, exist_ok=True)
        output = os.path.join(self.build_folder, "w_scan")

        cflags = [
            "-fPIE",
            "-Wall",
            "-Wno-comment",
            "-Wno-unused-parameter",
            "-Werror=implicit-function-declaration",
            "-D_GNU_SOURCE",
            f'-I"{self.source_folder}"',
        ]
        build_type = str(self.settings.build_type)
        if build_type == "Debug":
            cflags.extend(["-O0", "-g"])
        elif build_type == "RelWithDebInfo":
            cflags.extend(["-O2", "-g", "-DNDEBUG"])
        elif build_type == "MinSizeRel":
            cflags.extend(["-Os", "-DNDEBUG"])
        else:
            cflags.extend(["-O2", "-DNDEBUG"])
        if self._compiler_is_clang():
            cflags.append("-Qunused-arguments")

        sources = " ".join(
            f'"{os.path.join(self.source_folder, source)}"'
            for source in self._SOURCES
        )
        self.run(
            f'"{cc}" {" ".join(cflags)} {sources} -o "{output}" '
            "-pie -Wl,-z,relro,-z,now",
            cwd=self.source_folder,
            env="conanbuild",
        )

        if can_run(self):
            self.run(f'"{output}" -V', env="conanrun")

    def package(self):
        copy(
            self,
            "w_scan",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "bin"),
        )
        copy(
            self,
            "w_scan.1",
            src=os.path.join(self.source_folder, "doc"),
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        binary = os.path.join(self.package_folder, "bin", "w_scan")
        if os.path.exists(binary):
            os.chmod(binary, 0o755)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
