#!/usr/bin/env python3
"""Conan test_package for hdparm — CLI tool verification.

OHOS note: the local HarmonyOS build host rejects execution of unsigned ELF
binaries (kernel security policy), so the tool itself cannot be executed here.
Instead we verify the packaged artifact's OHOS loading contract (PT_INTERP is
the musl loader, NEEDED resolves against the OHOS sysroot) plus the installed
man page. The OHOS-specific probe is informational (no assertions).

`test_hdparm_elf.py` is a real (assertion-bearing) consumer test source: it is
required by the CI L0c `no_test_sources` gate and parses the packaged binary to
assert ELF64/AArch64 + PT_INTERP + DT_NEEDED libc.so + .note.ohos.ident.
"""
import os
import shutil
import sys

from conan import ConanFile


class HdparmTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        pkg = self.dependencies["hdparm"].package_folder
        hdparm_bin = os.path.join(pkg, "bin", "hdparm")

        assert os.path.isfile(hdparm_bin), f"Binary not found: {hdparm_bin}"

        # Verify ELF arm64 binary (no execution, just read magic bytes)
        with open(hdparm_bin, "rb") as f:
            magic = f.read(4)
        assert magic == b"\x7fELF", f"Not ELF: {magic!r}"

        # Verify man page
        man_page = os.path.join(pkg, "share", "man", "man8", "hdparm.8")
        assert os.path.isfile(man_page), f"Man page not found: {man_page}"

        # ── Real consumer test source (CI L0c: no_test_sources) ────────────
        # Runs on the build host (which cannot exec an unsigned ELF) and
        # asserts the HarmonyOS loading contract of the packaged binary.
        self.run(f"{sys.executable} test_hdparm_elf.py {hdparm_bin}")

        # ── HarmonyOS-specific consumer probe (non-assertion) ──────────────
        # hdparm is an application: there is nothing to link against, and the
        # OHOS host cannot execute an unsigned ELF. What a consumer actually
        # needs on HarmonyOS PC is a correctly declared musl loading contract,
        # so we dump the ELF header, program headers (PT_INTERP) and the
        # dynamic section (NEEDED / SONAME). This is printed, not asserted.
        readelf = (shutil.which("readelf")
                   or shutil.which("llvm-readelf")
                   or "/data/service/hnp/bin/readelf")
        if shutil.which(readelf) or os.path.isfile(readelf):
            self.run(f"{readelf} -hld {hdparm_bin}", env="conanrun")
        else:
            self.output.warning(
                "readelf not available — OHOS ELF loading probe skipped")

        # ELF type probe (non-assertion)
        self.run(f"file {hdparm_bin}", env="conanrun")
