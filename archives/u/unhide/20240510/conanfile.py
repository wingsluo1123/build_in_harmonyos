#!/usr/bin/env python3
"""Conan recipe — unhide 20240510 (forensic tool for hidden processes / ports).

unhide is a forensic tool that looks for hidden processes and TCP/UDP ports
(rootkits / LKMs / other hiding techniques).  Upstream ships no build system:
``build_all.sh`` invokes gcc directly to produce four binaries
(``unhide-linux`` with ``-pthread``, ``unhide_rb``, ``unhide-tcp``,
``unhide-posix``) with ``--static``.  ``build()`` runs the same compile+link
command per binary, dropping ``--static``: the OHOS sysroot has no static libc
and no rcrt1.o, so a static link cannot resolve (``sockstat 0.4.2`` precedent).
The driver default produces a dynamically linked PIE whose only NEEDED entry
is ``libc.so``; it runs natively on the OHOS device (musl loader) and through
qemu-aarch64 elsewhere.

Patches (portable, no platform macros):
  * ``<wait.h>`` -> ``<sys/wait.h>`` — glibc (and Ubuntu's libc6-dev) ship a
    ``wait.h`` redirect to ``sys/wait.h``; musl does not (nwipe 0.39 precedent);
  * add ``#include <limits.h>`` to the two files that use ``PATH_MAX`` —
    glibc satisfied it transitively, the OHOS musl headers need the explicit
    include.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class UnhideConan(ConanFile):
    name = "unhide"
    version = "20240510"
    description = "unhide - forensic tool to find hidden processes and TCP/UDP ports (rootkit / LKM detection)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/YJesus/Unhide"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("forensics", "security", "rootkit", "cli")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    # object lists of upstream build_all.sh (link flag -pthread only for
    # unhide-linux, exactly as upstream)
    _targets = {
        "unhide-linux": (["unhide-linux.c", "unhide-linux-bruteforce.c",
                          "unhide-linux-compound.c", "unhide-linux-procfs.c",
                          "unhide-linux-syscall.c", "unhide-output.c"], True),
        "unhide_rb": (["unhide_rb.c"], False),
        "unhide-tcp": (["unhide-tcp.c", "unhide-tcp-fast.c",
                        "unhide-output.c"], False),
        "unhide-posix": (["unhide-posix.c"], False),
    }

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("unhide 20240510 is prepared for Linux/OHOS targets only")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", check_type=dict, default={})
        cc = compilers.get("c", "cc")
        opt = "-O2" if str(self.settings.build_type) == "Release" else "-O0 -g"
        for target, (sources, need_pthread) in self._targets.items():
            pthread = " -pthread" if need_pthread else ""
            self.run(f"'{cc}' -Wall -Werror=implicit-function-declaration "
                     f"{opt}{pthread} -I. -o {target} {' '.join(sources)}",
                     env="conanbuild", cwd=self.source_folder)

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        for target in self._targets:
            copy(self, target, src=self.source_folder, dst=bindir)
            os.chmod(os.path.join(bindir, target), 0o755)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*.8", src=os.path.join(self.source_folder, "man"),
             dst=os.path.join(self.package_folder, "share", "man", "man8"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
