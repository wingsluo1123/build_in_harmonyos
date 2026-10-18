#!/usr/bin/env python3
"""Conan test_package for slcfitsio 0.4.7-pre.19.

R34: the test executes the installed artifact.  There is no libslcfitsio to
link a C program against — slcfitsio is an S-Lang module loaded through
dlopen() by the interpreter — so the consumer test drives the real `slsh`
binary (from the slang package) with the packaged `cfitsio-module.so` and the
packaged S-Lang wrappers, and runs **both** upstream regression scripts:

    test_fits.sl   image + binary table write/read round-trips
    test_wcs.sl    fitswcs bin/rebin (CRPIX / CDELT assertions)

each reported as its own `UPSTREAM_CASE PASS|FAIL ...` line followed by
`UPSTREAM_SUMMARY <passed>/<total>` in the conan log.

Execution happens wherever the target can actually run:
  * OHOS CI worker — the CI profile is used for both host and build context
    (`-pr:h=ohos-aarch64 -pr:b=ohos-aarch64`), so Conan does not consider it
    cross building, `can_run()` is true and `slsh` runs natively.  CI build
    #93516 executed both scripts with rc=0.
  * WSL cross build — the aarch64 OHOS `slsh` runs under this box's
    binfmt/qemu-aarch64; the driver injects the /opt/ohos-guest guest shims
    when present.  Pass `-c tools.build.cross_building:can_run=true` so that
    `test()` is entered instead of skipping.
When `can_run()` is false the run is reported as skipped rather than silently
pretending to pass.
"""

import os

from conan import ConanFile
from conan.tools.build import can_run


class SlcfitsioTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info(
                "slcfitsio test_package: cross-built target cannot be executed "
                "on this host -> run step skipped (pass "
                "-c tools.build.cross_building:can_run=true to run it under the "
                "local qemu-aarch64 emulator, or let the OHOS worker run it "
                "natively)")
            return

        package_folder = self.dependencies[
            self.tested_reference_str].package_folder
        driver = os.path.join(self.source_folder, "run_test.sh")
        self.run('sh "%s" "%s"' % (driver, package_folder), env="conanrun")
