#!/usr/bin/env python3
"""indi-playerone test_package — consumer end-to-end suite against the packaged
driver and the vendor POA SDK.

indi-playerone is an INDI driver (application package). It ships:

  * bin/indi_playerone_ccd            — the driver executable (links
                                        libindidriver.so.2 + libPlayerOneCamera.so.3)
  * bin/playerone_camera_test         — the vendor SDK test utility
  * share/indi/indi_playerone.xml     — the INDI device descriptor

The driver needs a physical PlayerOne Astronomy camera over USB, and the
vendor SDK has no simulation mode, so the packaged driver is validated
*statically* (HC-1 ELF, HC-2 framework/vendor linkage + embedded driver
logic strings, HC-4 device descriptor, HC-5 OHOS aarch64 target).

The functional core — the vendor POA SDK — is proven consumable by a real
downstream link (HC-3, R34): the probe translation unit includes the packaged
PlayerOneCamera.h, references the core public API and links against the
packaged libPlayerOneCamera.so.3 with the OHOS clang (compile+link, not run —
the CI sandbox refuses to dlopen foreign .so files and there is no camera).
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException


class IndiPlayeroneTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Functional core: the probe links the vendor POA SDK directly, so
        # the test package requires it independently of the application
        # package.
        self.requires("libplayerone/3.1.0")

    def _clang_path(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        c = compilers.get("c")
        candidates = []
        if c:
            candidates.append(os.path.realpath(c))
        found = os.environ.get("CC")
        if found:
            candidates.append(os.path.realpath(found))
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return "clang"

    def _assert(self, cond, msg):
        if not cond:
            raise ConanException(f"assertion FAILED: {msg}")
        self.output.success(f"assert: {msg}")

    def layout(self):
        pass

    # Explicit no-op: the default build() would try to apply the *package*
    # conandata.yml patches against the test tree (no CMakeLists here); the
    # actual compilation happens in test() via self.run.
    def build(self):
        pass

    def test(self):
        pkg = self.dependencies["indi-playerone"].package_folder
        driver = os.path.join(pkg, "bin", "indi_playerone_ccd")
        device_xml = os.path.join(pkg, "share", "indi", "indi_playerone.xml")
        for required in (driver, device_xml):
            if not os.path.isfile(required):
                raise AssertionError(
                    f"packaged artifact {required} is missing — the consumer "
                    "suite asserts on the shipped package, not on bookkeeping")

        # ── HC-3: real downstream link against the packaged vendor SDK ──
        lpo = self.dependencies["libplayerone"]
        lpo_inc = os.path.join(lpo.package_folder, lpo.cpp_info.includedirs[0])
        lpo_lib = os.path.join(lpo.package_folder, lpo.cpp_info.libdirs[0])
        vendor_so = os.path.join(lpo_lib, "libPlayerOneCamera.so.3")
        self._assert(os.path.isfile(vendor_so),
                     "libPlayerOneCamera.so.3 packaged in libplayerone dep")

        src = os.path.join(self.recipe_folder, "ipo_probe.c")
        if not os.path.isfile(src):
            raise AssertionError(f"test source {src} is missing")
        obj = os.path.join(self.build_folder, "ipo_probe.o")
        elf = os.path.join(self.build_folder, "ipo_probe.so")
        cc = self._clang_path()
        self.run(
            f"{cc} --target=aarch64-linux-ohos -I{lpo_inc} -c {src} -o {obj}",
            scope="build",
        )
        self._assert(os.path.isfile(obj), "probe compiles with OHOS clang")
        self.run(
            f"{cc} --target=aarch64-linux-ohos -shared {obj} -o {elf} {vendor_so}",
            scope="build",
        )
        self._assert(os.path.isfile(elf) and os.path.getsize(elf) > 0,
                     "probe links against packaged vendor .so (R34, HC-3)")

        # ── HC-1/2/4/5: static suite against the packaged driver ──
        out = os.path.join(self.build_folder, "test_playerone")
        log = os.path.join(self.build_folder, "test_playerone.log")
        cc_plain = self.conf.get("tools.build:compiler_executables", default={}).get(
            "c", "clang")
        self.run(f"{cc_plain} -std=c99 {os.path.join(self.recipe_folder, 'test_playerone.c')} -o {out}",
                 scope="build")
        self.run(f"{out} {driver} {device_xml} {log}", scope="build")

        if not os.path.isfile(log):
            raise AssertionError(f"test_playerone produced no result log at {log}")
        with open(log, encoding="utf-8", errors="replace") as fh:
            summary = fh.read()

        print(f"[test_playerone] {summary.strip()}")
        checks = re.search(r"checks=(\d+) failures=(\d+) result=(\w+)", summary)
        if not checks:
            raise AssertionError(f"unparseable test_playerone summary:\n{summary}")
        if checks.group(3) != "PASSED":
            raise AssertionError(f"test_playerone FAILED:\n{summary}")
        if int(checks.group(1)) == 0:
            raise AssertionError("test_playerone produced no checks — hollow test")
