#!/usr/bin/env python3
"""Conan recipe for librem-ec 0.9.2 — Purism Librem EC ACPI kernel module.

librem-ec-acpi is a Linux Kbuild external module (obj-m := librem_ec_acpi.o)
exposing the Librem 14 embedded-controller ACPI interface (battery thresholds,
LEDs, hotkeys, fan/thermal). It requires Linux kernel headers and a configured
kernel build tree and loads as librem_ec_acpi.ko via DKMS.

NOTE: HarmonyOS (OHOS) ships no Linux kernel headers or Kbuild tree suitable
for external module compilation. The build is therefore intentionally a no-op;
the recipe packages a source snapshot from the pinned upstream tarball so the
test_package can verify the module contract without claiming the module was
built or loaded.

Upstream: https://source.puri.sm/nicole.faerber/librem-ec-acpi-dkms (tag v0.9.2)
License: GPL-2.0-only
"""

import os

from conan import ConanFile
from conan.tools.files import copy, get


class LibremEcConan(ConanFile):
    name = "librem-ec"
    version = "0.9.2"
    description = (
        "Purism Librem 14 embedded-controller ACPI driver "
        "(Linux kernel module; source snapshot on HarmonyOS)."
    )
    license = "GPL-2.0-only"
    homepage = "https://source.puri.sm/nicole.faerber/librem-ec-acpi-dkms"
    url = ""

    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # librem-ec-acpi is a Kbuild kernel module (obj-m := librem_ec_acpi.o).
        # It requires Linux kernel headers (linux/module.h, linux/acpi.h,
        # linux/leds.h, linux/power_supply.h, acpi/battery.h) plus a configured
        # kernel build tree (/lib/modules/$(uname -r)/build), neither of which
        # exists in the OHOS sysroot. Build stays empty on purpose; nothing to
        # compile without kernel headers, and no stub is faked.
        pass

    def package(self):
        copy(self, "librem_ec_acpi.c", src=self.source_folder,
             dst=os.path.join(self.package_folder, "src"))
        copy(self, "Makefile", src=self.source_folder,
             dst=os.path.join(self.package_folder, "src"))
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "src"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "src"))

    def package_info(self):
        # Kernel module — no user-visible C/C++ library.
        pass
