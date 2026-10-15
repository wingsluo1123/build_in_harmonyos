#!/usr/bin/env python3
"""test_package — HarmonyOS consumer test for the packaged shogivar 1.55b.

ShogiVar is a GTK+ 3 application without a testable public API, so this
consumer test asserts the two contracts a dependent of the package actually
relies on:

  * the installed ``bin/shogivar`` is a well-formed OHOS aarch64 executable
    whose dynamic section really pulls in the GTK+ 3 stack (parsed here in
    Python, no readelf needed), and
  * the installed run-time asset tree plus the display-less CLI entry points
    behave as documented — driven by ``test.sh`` from the consumer side.
"""
import os
import struct

from conan import ConanFile


def read_needed(path):
    """Return (e_machine, interp, [DT_NEEDED...]) for a 64-bit little-endian ELF."""
    with open(path, "rb") as fh:
        blob = fh.read()
    if blob[:4] != b"\x7fELF":
        raise AssertionError("not an ELF file")
    if blob[4] != 2 or blob[5] != 1:
        raise AssertionError("not a 64-bit little-endian ELF")
    e_machine, = struct.unpack_from("<H", blob, 18)
    e_phoff, = struct.unpack_from("<Q", blob, 32)
    e_phentsize, e_phnum = struct.unpack_from("<HH", blob, 54)

    loads, interp, dynamic = [], None, None
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type, _flags, p_offset, p_vaddr, _pa, p_filesz, _msz, _al = \
            struct.unpack_from("<IIQQQQQQ", blob, off)
        if p_type == 1:      # PT_LOAD
            loads.append((p_vaddr, p_offset, p_filesz))
        elif p_type == 3:    # PT_INTERP
            interp = blob[p_offset:p_offset + p_filesz].split(b"\0")[0].decode()
        elif p_type == 2:    # PT_DYNAMIC
            dynamic = (p_offset, p_filesz)

    def vaddr_to_off(addr):
        for p_vaddr, p_offset, p_filesz in loads:
            if p_vaddr <= addr < p_vaddr + p_filesz:
                return addr - p_vaddr + p_offset
        raise AssertionError(f"vaddr {addr:#x} not covered by any PT_LOAD")

    needed = []
    if dynamic:
        d_off, d_size = dynamic
        strtab = strsz = None
        entries = []
        for i in range(d_size // 16):
            d_tag, d_val = struct.unpack_from("<qQ", blob, d_off + i * 16)
            entries.append((d_tag, d_val))
            if d_tag == 5:       # DT_STRTAB
                strtab = vaddr_to_off(d_val)
            elif d_tag == 10:    # DT_STRSZ
                strsz = d_val
            elif d_tag == 0:     # DT_NULL
                break
        assert strtab is not None and strsz, "no DT_STRTAB/DT_STRSZ"
        for d_tag, d_val in entries:
            if d_tag == 1:       # DT_NEEDED
                end = blob.index(b"\0", strtab + d_val)
                needed.append(blob[strtab + d_val:end].decode())
    return e_machine, interp, needed


class ShogivarTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["shogivar"].package_folder
        binary = os.path.join(pkg, "bin", "shogivar")
        assert os.path.isfile(binary), f"bin/shogivar not packaged: {binary}"

        checks = []
        e_machine, interp, needed = read_needed(binary)
        checks.append(("ELF64 little-endian aarch64 executable",
                       e_machine == 0xB7))
        self.output.info(f"  e_machine={e_machine:#x} interp={interp} "
                         f"needed={len(needed)} libs")
        checks.append(("PT_INTERP is the OHOS musl loader",
                       interp == "/lib/ld-musl-aarch64.so.1"))
        for lib in ("libgtk-3.so.0", "libcairo.so.2",
                    "libglib-2.0.so.0", "libpango-1.0.so.0"):
            checks.append((f"DT_NEEDED contains {lib}", lib in needed))

        failed = [name for name, good in checks if not good]
        for name, good in checks:
            self.output.info(("  ok   " if good else "  FAIL ") + name)
        assert not failed, f"ELF/dynamic-link contract failed: {failed}"

        # OHOS /system/bin/sh (mksh) cannot be relied upon to execute ELF
        # binaries, so prefer a real bash.
        bash = os.environ.get("CONFIG_SHELL", "")
        if os.path.basename(bash) != "bash":
            bash = "/data/service/hnp/bin/bash"
            if not os.path.isfile(bash):
                bash = "bash"
        script = os.path.join(self.source_folder, "test.sh")
        self.output.info(f"running consumer suite: {bash} {script} {pkg}")
        self.run(f"'{bash}' '{script}' '{pkg}'", env="conanrun")
