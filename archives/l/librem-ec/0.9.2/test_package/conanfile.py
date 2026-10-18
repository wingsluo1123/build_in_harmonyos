#!/usr/bin/env python3
"""Conan test_package for librem-ec 0.9.2.

librem-ec-acpi is a **Linux kernel module** (librem_ec_acpi.ko). Its only
consumer is the kernel itself: after insmod into a running Linux kernel with
matching headers, userspace observes LEDs, hwmon, power-supply and input
devices. Loading plus invocation can ONLY happen on real Purism hardware with
kernel headers and root — impossible inside the OHOS worker (no kernel tree,
no insmod, no ACPI firmware interface).

Per the adaptation rules a test_package MUST exercise the package and MUST
NOT fake a pass. Since there is no userspace binary and no callable userspace
API, the honest check is:

  1. Run a REAL check (via self.run) that the packaged kernel-module source
     carries the ACPI driver contract (module licence, ACPI device table with
     the Purism 316D4C14/PURI4543 IDs, Kbuild obj-m evidence, LED/hwmon/
     power-supply/battery-threshold entry points). A missing source is a hard
     failure (exit 2), never a skipped pass.
  2. Explicitly report that kernel-state load/invoke verification remains
     0/1 and is not executed in CI.

The CI test_package result therefore means "source contract: 8/8 assertions
passed", not "kernel module functionality: passed".
"""

import os
import stat

from conan import ConanFile
from conan.errors import ConanException


class LibremEcTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["librem-ec"].package_folder

        module_c = os.path.join(pkg_folder, "src", "librem_ec_acpi.c")
        if not os.path.isfile(module_c):
            for root, _dirs, files in os.walk(pkg_folder):
                if "librem_ec_acpi.c" in files:
                    module_c = os.path.join(root, "librem_ec_acpi.c")
                    break

        if not os.path.isfile(module_c):
            raise ConanException(
                "[librem-ec] BLOCKED: packaged librem_ec_acpi.c is missing "
                f"(looked under {pkg_folder}); no source-contract assertion ran"
            )

        check_sh = os.path.join(self.source_folder, "check_source.sh")
        try:
            os.chmod(check_sh, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
        except OSError:
            pass
        try:
            self.run(f'sh "{check_sh}" "{module_c}"', env="conanrun")
        except Exception as exc:
            raise ConanException(
                "[librem-ec] BLOCKED: source-contract check did not pass; "
                f"kernel functionality remains unverified: {exc}"
            ) from exc

        self.output.warning(
            "[librem-ec] PARTIAL: source contract verified (8/8 assertions). "
            "Kernel load/invoke requires Purism hardware with matching kernel "
            "headers + root; functional verification remains 0/1."
        )
