#!/usr/bin/env python3
"""Consumer checks for the indi-sbig package.

usage: check_driver.py <bindir> <indi_sbig.xml> <indi-lib-dir> <libusb-lib-dir>

indi-sbig ships one INDI driver plus a descriptor that registers two devices
against it:

    bin/indi_sbig_ccd    — SBIG CCD camera driver (driver name "SBIG CCD")
    share/indi/indi_sbig.xml — declares "SBIG CCD" and "SBIG ST-I"

Checks (all of them inspect the packaged artefacts only):
  1. bin/indi_sbig_ccd exists, is a non-empty AArch64 ELF64 executable.
  2. share/indi/indi_sbig.xml declares both devices ("SBIG CCD", "SBIG ST-I"),
     each pointing at bin/indi_sbig_ccd which really is shipped.
  3. the driver's DT_NEEDED closure is complete: the INDI core libraries
     (libindidriver / libindiAlignmentDriver) and libusb-1.0 are recorded, every
     entry is a plain soname, and the libraries exist in the packages the
     closure points at.
  4. best effort: the loader is asked to start the driver.  A real closure
     defect always fails; only an *evidence-backed* host refusal is skipped.
"""
import os
import re
import struct
import subprocess
import sys

EXPECTED_EM_AARCH64 = 0xB7
DRIVER = "indi_sbig_ccd"
DEVICE_LABELS = ("SBIG CCD", "SBIG ST-I")
INDI_CORE_LIBS = ("libindidriver.so.2", "libindiAlignmentDriver.so.2")
USB_LIB = "libusb-1.0.so.0"
PLATFORM_LIMITS = ("not signed", "unsigned", "signature",
                   "operation not permitted", "permission denied")

fails = []
skips = []


def fail(msg):
    fails.append(msg)
    print("[FAIL] %s" % msg)


def ok(msg):
    print("[ok]   %s" % msg)


def skip(msg):
    skips.append(msg)
    print("[skip] %s" % msg)


def check_elf(driver):
    if not os.path.isfile(driver):
        fail("driver binary is missing: %s" % driver)
        return False
    size = os.path.getsize(driver)
    if size < 4096:
        fail("driver binary is suspiciously small (%d bytes)" % size)
        return False
    with open(driver, "rb") as fh:
        head = fh.read(64)
    if head[:4] != b"\x7fELF":
        fail("driver is not an ELF file (magic=%r)" % head[:4])
        return False
    if struct.unpack("<H", head[18:20])[0] != EXPECTED_EM_AARCH64:
        fail("driver is not an AArch64 ELF")
        return False
    if head[4] != 2:
        fail("driver is not a 64-bit ELF (EI_CLASS=%d)" % head[4])
        return False
    ok("bin/%s: AArch64 ELF64, %d bytes" % (os.path.basename(driver), size))
    return True


def check_xml(xml, bindir):
    if not os.path.isfile(xml):
        fail("INDI data file is missing: %s" % xml)
        return
    text = open(xml, encoding="utf-8", errors="replace").read()
    if DRIVER not in text:
        fail("INDI data file does not reference %s" % DRIVER)
        return
    if not os.path.isfile(os.path.join(bindir, DRIVER)):
        fail("the executable referenced by the INDI data file is not in bin/")
        return
    # The descriptor lists the second device through <device label="SBIG ST-I">
    # while both entries point at the same driver name ("SBIG CCD").
    for label in DEVICE_LABELS:
        if 'label="%s"' % label not in text:
            fail("INDI data file does not declare the '%s' device (label=)" % label)
            return
    if 'name="SBIG CCD"' not in text:
        fail('INDI data file does not declare the driver name "SBIG CCD"')
        return
    ok("share/indi/indi_sbig.xml: declares %s -> bin/%s"
       % (" / ".join("'%s'" % l for l in DEVICE_LABELS), DRIVER))


def read_needed(driver):
    data = open(driver, "rb").read()
    e_phoff = struct.unpack_from("<Q", data, 0x20)[0]
    e_phentsize = struct.unpack_from("<H", data, 0x36)[0]
    e_phnum = struct.unpack_from("<H", data, 0x38)[0]
    loads, dynamic = [], None
    for idx in range(e_phnum):
        off = e_phoff + idx * e_phentsize
        p_type = struct.unpack_from("<I", data, off)[0]
        if p_type not in (1, 2):
            continue
        p_offset = struct.unpack_from("<Q", data, off + 0x08)[0]
        p_vaddr = struct.unpack_from("<Q", data, off + 0x10)[0]
        p_filesz = struct.unpack_from("<Q", data, off + 0x20)[0]
        if p_type == 1:
            loads.append((p_vaddr, p_offset, p_filesz))
        else:
            dynamic = (p_offset, p_filesz)
    if dynamic is None:
        raise ValueError("no PT_DYNAMIC segment")
    needed_offsets, strtab_vaddr, strtab_size = [], None, 0
    dyn_off, dyn_size = dynamic
    for idx in range(dyn_size // 16):
        d_tag, d_val = struct.unpack_from("<qQ", data, dyn_off + idx * 16)
        if d_tag == 1:
            needed_offsets.append(d_val)
        elif d_tag == 5:
            strtab_vaddr = d_val
        elif d_tag == 10:
            strtab_size = d_val
    if strtab_vaddr is None:
        raise ValueError("no DT_STRTAB entry")
    strtab_off = None
    for vaddr, p_offset, p_filesz in loads:
        if vaddr <= strtab_vaddr < vaddr + p_filesz:
            strtab_off = p_offset + (strtab_vaddr - vaddr)
            break
    if strtab_off is None:
        raise ValueError("DT_STRTAB does not live inside a PT_LOAD segment")
    strtab = data[strtab_off:strtab_off + strtab_size]
    names = []
    for name_off in needed_offsets:
        end = strtab.find(b"\0", name_off)
        if end < 0:
            raise ValueError("unterminated DT_NEEDED entry")
        names.append(strtab[name_off:end].decode("utf-8", "replace"))
    return names


def check_linkage(driver, indi_libdir, usb_libdir):
    try:
        needed = read_needed(driver)
    except Exception as exc:
        fail("could not read the driver's dynamic section: %s" % exc)
        return
    absolute = [e for e in needed if e.startswith("/")]
    if absolute:
        fail("DT_NEEDED holds absolute paths: %s" % ", ".join(absolute))
        return
    missing = [lib for lib in INDI_CORE_LIBS if lib not in needed]
    if missing:
        fail("driver does not link the INDI core libraries %s (DT_NEEDED=%s)"
             % (", ".join(missing), ", ".join(needed)))
        return
    absent = [lib for lib in INDI_CORE_LIBS
              if not os.path.isfile(os.path.join(indi_libdir, lib))]
    if absent:
        fail("INDI core libraries missing from %s: %s"
             % (indi_libdir, ", ".join(absent)))
        return
    if USB_LIB not in needed:
        fail("DT_NEEDED does not record %s (DT_NEEDED=%s)" % (USB_LIB, ", ".join(needed)))
        return
    if not os.path.isfile(os.path.join(usb_libdir, USB_LIB)):
        fail("%s is not present in the libusb package libdir %s" % (USB_LIB, usb_libdir))
        return
    ok("DT_NEEDED closure complete (%s, %s)"
       % (", ".join(INDI_CORE_LIBS), USB_LIB))


def _host_can_map(path):
    try:
        import ctypes
        ctypes.CDLL(path, mode=ctypes.RTLD_GLOBAL)
        return True, None
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _classify_loader(text, dep_libdirs):
    low = text.lower()
    named = set(re.findall(r"error loading shared library ([^:\s]+)", low))
    named.update(re.findall(r"cannot open shared object file: ([^\s,]+)", low))
    missing = []
    host_refused = any(tag in low for tag in PLATFORM_LIMITS)
    for entry in sorted(named):
        path = next((os.path.join(d, entry) for d in dep_libdirs
                     if os.path.isfile(os.path.join(d, entry))), None)
        if path is None:
            missing.append(entry)
            continue
        loadable, why = _host_can_map(path)
        if loadable:
            missing.append("%s（宿主可映射，但驱动加载失败）" % entry)
        elif any(tag in (why or "").lower()
                 for tag in ("permission", "not permitted", "operation")):
            host_refused = True
        else:
            missing.append("%s（宿主加载失败：%s）" % (entry, why))
    return missing, host_refused


def check_exec(driver, dep_libdirs):
    try:
        proc = subprocess.run([driver, "--help"], stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=15)
        out = proc.stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        ok("driver started and stayed alive until the 15s timeout (closure resolved)")
        return
    except OSError as exc:
        if any(tag in str(exc).lower() for tag in PLATFORM_LIMITS):
            skip("host refused to start the OHOS binary: %s" % exc)
        else:
            fail("could not execute the driver: %s" % exc)
        return
    low = out.lower()
    loader_tags = ("error loading shared library", "error relocating",
                   "cannot open shared object", "symbol not found",
                   "no such file or directory: lib")
    if not any(tag in low for tag in loader_tags):
        ok("driver exec'd cleanly (exit=%s, no unresolved shared library)" % proc.returncode)
        return
    missing, host_refused = _classify_loader(out, dep_libdirs)
    if missing:
        fail("加载器点名了缺失/无法加载的库 → 真实缺陷：%s（输出：%s）"
             % ("，".join(missing), out.strip()[:200]))
        return
    if host_refused:
        skip("宿主拒绝映射依赖库（有证据），非打包缺陷：%s" % out.strip()[:200])
        return
    fail("加载器报出未解析的共享库闭包且无宿主拒绝证据 → 真实缺陷：%s" % out.strip()[:300])


def main():
    if len(sys.argv) != 5:
        print(__doc__)
        return 2
    bindir, xml, indi_libdir, usb_libdir = sys.argv[1:5]
    driver = os.path.join(bindir, DRIVER)
    if check_elf(driver):
        check_linkage(driver, indi_libdir, usb_libdir)
        check_exec(driver, [indi_libdir, usb_libdir])
    check_xml(xml, bindir)
    print("checks=4 fails=%d skips=%d" % (len(fails), len(skips)))
    if fails:
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
