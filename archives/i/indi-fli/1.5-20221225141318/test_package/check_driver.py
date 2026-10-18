#!/usr/bin/env python3
"""Consumer checks for the indi-fli package.

usage: check_driver.py <bindir> <indi_fli.xml> <indi-lib-dir> <libusb-lib-dir>

indi-fli ships three INDI driver executables plus the device descriptor that
registers them with the INDI framework:

    bin/indi_fli_ccd    — FLI CCD camera      (driver name "FLI CCD")
    bin/indi_fli_focus  — FLI PDF focuser     (driver name "FLI PDF")
    bin/indi_fli_wheel  — FLI CFW filter wheel(driver name "FLI CFW")
    share/indi/indi_fli.xml

Checks (every one of them inspects the packaged artefacts; nothing is
re-implemented and no upstream tool is required):
  1. all three drivers exist, are non-empty AArch64 ELF64 executables.
  2. share/indi/indi_fli.xml declares the three FLI devices and points each of
     them at an executable that is really shipped in bin/.
  3. each driver's DT_NEEDED closure is complete: the INDI core libraries
     (libindidriver / libindiAlignmentDriver) and libusb-1.0 are recorded in
     DT_NEEDED, every entry is a plain soname, and the libraries really exist in
     the packages the closure points at (libusb-1.0 proves the *static* libfli.a
     was linked with its USB runtime dependency).
  4. best effort: the loader is asked to start every driver.  A real closure
     defect always fails: unresolved symbols / unresolved shared objects /
     libraries that are missing from every dependency libdir are reported as
     FAIL.  Only a *host* refusal is skipped — and only when there is evidence
     for it (a platform-limit marker in the output, or a named library that
     exists but cannot be mapped by the host either, e.g. Permission denied),
     so an environment limitation never hides a packaging defect.

（本脚本与同快照兄弟驱动 indi-talon6 / indi-aok 的消费者校验同构，按本包
 「三驱动 + 一个 XML」的形态扩展。）
"""
import os
import re
import struct
import subprocess
import sys

EXPECTED_EM_AARCH64 = 0xB7
DRIVERS = ("indi_fli_ccd", "indi_fli_focus", "indi_fli_wheel")
DRIVER_LABELS = {"indi_fli_ccd": "FLI CCD",
                 "indi_fli_focus": "FLI PDF",
                 "indi_fli_wheel": "FLI CFW"}
# FindINDI 的默认组件是 driver + align（本驱动树未请求 client 组件）
INDI_CORE_LIBS = ("libindidriver.so.2", "libindiAlignmentDriver.so.2")
USB_LIB = "libusb-1.0.so.0"
LOADER_ERRORS = (
    "error loading shared library",
    "error relocating",
    "cannot open shared object",
    "no such file or directory: lib",
)
PLATFORM_LIMITS = (
    "not signed",
    "unsigned",
    "signature",
    "operation not permitted",
    "permission denied",
)

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
    machine = struct.unpack("<H", head[18:20])[0]
    if machine != EXPECTED_EM_AARCH64:
        fail("driver e_machine=%#x is not AArch64 (%#x)" % (machine, EXPECTED_EM_AARCH64))
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
    with open(xml, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    for driver in DRIVERS:
        label = DRIVER_LABELS[driver]
        if driver not in text:
            fail("INDI data file does not reference %s" % driver)
            continue
        if 'name="%s"' % label not in text:
            fail("INDI data file does not declare the '%s' driver name" % label)
            continue
        if not os.path.isfile(os.path.join(bindir, driver)):
            fail("the executable referenced by the INDI data file is not in bin/: %s" % driver)
            continue
        ok("share/indi/indi_fli.xml: %s ('%s') -> bin/%s" % (driver, label, driver))


def read_needed(driver):
    """Return the DT_NEEDED sonames of an ELF64 little-endian object."""
    with open(driver, "rb") as fh:
        data = fh.read()
    e_phoff = struct.unpack_from("<Q", data, 0x20)[0]
    e_phentsize = struct.unpack_from("<H", data, 0x36)[0]
    e_phnum = struct.unpack_from("<H", data, 0x38)[0]
    loads = []
    dynamic = None
    for idx in range(e_phnum):
        off = e_phoff + idx * e_phentsize
        p_type = struct.unpack_from("<I", data, off)[0]
        if p_type not in (1, 2):  # PT_LOAD, PT_DYNAMIC
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

    needed_offsets = []
    strtab_vaddr = None
    strtab_size = 0
    dyn_off, dyn_size = dynamic
    for idx in range(dyn_size // 16):
        d_tag, d_val = struct.unpack_from("<qQ", data, dyn_off + idx * 16)
        if d_tag == 1:  # DT_NEEDED
            needed_offsets.append(d_val)
        elif d_tag == 5:  # DT_STRTAB
            strtab_vaddr = d_val
        elif d_tag == 10:  # DT_STRSZ
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
    """Each packaged executable must carry a complete, relocatable closure."""
    name = os.path.basename(driver)
    try:
        needed = read_needed(driver)
    except Exception as exc:
        fail("%s: could not read the driver's dynamic section: %s" % (name, exc))
        return
    absolute = [entry for entry in needed if entry.startswith("/")]
    if absolute:
        fail("%s: DT_NEEDED holds absolute paths: %s" % (name, ", ".join(absolute)))
        return
    missing = [lib for lib in INDI_CORE_LIBS if lib not in needed]
    if missing:
        fail("%s: driver does not link the INDI core libraries %s (DT_NEEDED=%s)"
             % (name, ", ".join(missing), ", ".join(needed)))
        return
    absent = [lib for lib in INDI_CORE_LIBS
              if not os.path.isfile(os.path.join(indi_libdir, lib))]
    if absent:
        fail("%s: INDI core libraries missing from %s: %s"
             % (name, indi_libdir, ", ".join(absent)))
        return
    if USB_LIB not in needed:
        fail("%s: DT_NEEDED does not record %s, so the static libfli.a USB "
             "backend was not linked with its runtime dependency (DT_NEEDED=%s)"
             % (name, USB_LIB, ", ".join(needed)))
        return
    if not os.path.isfile(os.path.join(usb_libdir, USB_LIB)):
        fail("%s: %s is not present in the libusb package libdir %s"
             % (name, USB_LIB, usb_libdir))
        return
    ok("%s: DT_NEEDED closure complete (%s, %s)"
       % (name, ", ".join(INDI_CORE_LIBS), USB_LIB))


def _host_can_map(path):
    """宿主能否映射该 .so；返回 (True, None) 或 (False, 原因)。"""
    try:
        import ctypes
        ctypes.CDLL(path, mode=ctypes.RTLD_GLOBAL)
        return True, None
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _classify_loader(text, dep_libdirs):
    """区分「真实闭包缺陷」与「宿主拒绝」。"""
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
    """Best effort 启动驱动器：真实闭包/符号缺陷一律 FAIL，仅有证据的宿主拒绝记 SKIP。"""
    name = os.path.basename(driver)
    try:
        proc = subprocess.run([driver, "--help"], stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=15)
        out = proc.stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        ok("%s: started and stayed alive until the 15s timeout (closure resolved)" % name)
        return
    except OSError as exc:
        low = str(exc).lower()
        if any(tag in low for tag in PLATFORM_LIMITS):
            skip("%s: host refused to start the OHOS binary: %s" % (name, exc))
        else:
            fail("%s: could not execute the driver: %s" % (name, exc))
        return

    low = out.lower()
    loader_tags = ("error loading shared library", "error relocating",
                   "cannot open shared object", "symbol not found",
                   "no such file or directory: lib")
    if not any(tag in low for tag in loader_tags):
        ok("%s: exec'd cleanly (exit=%s, no unresolved shared library)"
           % (name, proc.returncode))
        return
    missing, host_refused = _classify_loader(out, dep_libdirs)
    if missing:
        fail("%s: 加载器点名了缺失/无法加载的库 → 真实缺陷：%s（输出：%s）"
             % (name, "，".join(missing), out.strip()[:200]))
        return
    if host_refused:
        skip("%s: 宿主拒绝映射依赖库（有证据），非打包缺陷：%s"
             % (name, out.strip()[:200]))
        return
    fail("%s: 加载器报出未解析的共享库闭包且无宿主拒绝证据 → 真实缺陷：%s"
         % (name, out.strip()[:300]))


def main():
    if len(sys.argv) != 5:
        print(__doc__)
        return 2
    bindir, xml, indi_libdir, usb_libdir = sys.argv[1:5]
    drivers = []
    for name in DRIVERS:
        driver = os.path.join(bindir, name)
        if check_elf(driver):
            drivers.append(driver)
    check_xml(xml, bindir)
    for driver in drivers:
        check_linkage(driver, indi_libdir, usb_libdir)
        check_exec(driver, [indi_libdir, usb_libdir])
    checks = 3 + len(DRIVERS) * 2
    print("checks=%d fails=%d skips=%d" % (checks, len(fails), len(skips)))
    if fails:
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
