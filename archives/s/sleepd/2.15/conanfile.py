#!/usr/bin/env python3
"""Conan recipe for sleepd 2.15 — laptop power-event daemon (Debian).

HarmonyOS (aarch64) adaptation.  sleepd is plain C shipping a hand-written
Makefile (no configure): it links ``-lpthread`` and reads ACPI/sysfs data at
runtime.  The recipe drives that Makefile directly and installs the two
binaries itself instead of using ``make install``.

Build notes:
* Upstream's ``install`` target runs ``install -m 4755 -o root -g root
  sleepctl`` (setuid root) and ``install -d`` — both misbehave/would need
  root on the device, so the recipe installs ``sleepd`` and ``sleepctl``
  itself with normal 0755 permissions.
* ``CFLAGS``/``LIBS`` are passed on the make command line, which *replaces*
  the Makefile's own ``CFLAGS += -DACPI_APM -pthread`` (a command-line
  variable wins over in-makefile appends), so the define is repeated here.
* ``-lpthread`` links cleanly on this toolchain (no separate libpthread
  needed; musl folds it into libc).
* ``<linux/input.h>`` (used by eventmonitor.c) is present in the OHOS
  sysroot.

R32: settings.os must check in ("Linux", "OHOS").
R38: package_type="application" ships bin/ tools -> archives/s/sleepd/commands.json.
R51: upstream ships no test suite (the Makefile has only all/clean/install);
     see notes.md, and functional coverage is provided by test_package.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class SleepdConan(ConanFile):
    name = "sleepd"
    version = "2.15"
    description = "Daemon to monitor power events and control suspend/hibernate policy"
    license = "GPL-2.0-or-later"
    homepage = "https://packages.debian.org/source/sleepd"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("sleepd is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        basic_layout(self)
        # Upstream ships a plain Makefile with no out-of-tree support.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        cc = os.environ.get("CC", "/data/service/hnp/bin/clang")
        # A command-line CFLAGS replaces the Makefile's `CFLAGS += ...`, so the
        # -DACPI_APM / -pthread pair must be restated here.
        cflags = "-O2 -g -Wall -DACPI_APM -pthread"
        self.run("make CC=%s CFLAGS='%s' LIBS='-lpthread'" % (cc, cflags),
                 cwd=self.source_folder)

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        mandir8 = os.path.join(self.package_folder, "share", "man", "man8")
        mandir1 = os.path.join(self.package_folder, "share", "man", "man1")
        copy(self, "sleepd", src=self.source_folder, dst=bindir)
        copy(self, "sleepctl", src=self.source_folder, dst=bindir)
        copy(self, "sleepd.8", src=self.source_folder, dst=mandir8)
        copy(self, "sleepctl.1", src=self.source_folder, dst=mandir1)
        copy(self, "GPL", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
