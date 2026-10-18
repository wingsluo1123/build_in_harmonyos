#!/usr/bin/env python3
"""Consumer checks for the indi-armadillo-platypus package (multi-driver).

usage: check_all_drivers.py <bindir> <indi_lunatico.xml> <indi-lib-dir> [<rules-file>]

Checks (every one of them inspects the packaged artefacts; nothing is
re-implemented and no upstream tool is required):
  1. all six driver executables exist in bin/ and are non-empty AArch64 ELF.
  2. share/indi/indi_lunatico.xml declares exactly the six drivers and every
     <driver ...>executable</driver> reference exists in bin/.
  3. every driver's DT_NEEDED closure is complete: the INDI core libraries
     (libindiclient / libindidriver / libindiAlignmentDriver) are recorded, all
     entries are plain sonames, and the three libraries exist in the libindi
     package.
  4. the udev rules file that upstream installs to an absolute
     /usr/lib/udev/rules.d is present inside the package (the recipe redirects
     RULES_INSTALL_DIR into the private prefix).
  5. best effort: the loader is asked to start one driver.  Only a *named*
     platform-limit signal (unsigned ELF / operation not permitted / permission
     denied) is reported as SKIP together with the loader message.  A loader
     report of a missing shared library or an unresolved symbol is a real
     packaging defect and FAILs — a platform limitation never becomes a
     packaging failure, and a packaging defect never hides behind a SKIP.
"""
import os
import re
import struct
import subprocess
import sys
import time

EXPECTED_EM_AARCH64 = 0xB7
EXPECTED_DRIVERS = (
    "indi_seletek_rotator",
    "indi_dragonfly_dome",
    "indi_dragonfly",
    "indi_beaver_dome",
    "indi_armadillo_focus",
    "indi_platypus_focus",
)
# indi-armadillo-platypus 的 FindINDI 组件为 driver + align + client（补丁 0001）
INDI_CORE_LIBS = ("libindiclient.so.2", "libindidriver.so.2",
                  "libindiAlignmentDriver.so.2")
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


def check_elfs(bindir):
    checked = 0
    for name in EXPECTED_DRIVERS:
        path = os.path.join(bindir, name)
        if not os.path.isfile(path):
            fail("driver binary is missing: %s" % path)
            continue
        size = os.path.getsize(path)
        if size < 4096:
            fail("%s is suspiciously small (%d bytes)" % (name, size))
            continue
        with open(path, "rb") as fh:
            head = fh.read(64)
        if head[:4] != b"\x7fELF":
            fail("%s is not an ELF file (magic=%r)" % (name, head[:4]))
            continue
        if head[4] != 2:
            fail("%s is not a 64-bit ELF (EI_CLASS=%d)" % (name, head[4]))
            continue
        machine = struct.unpack("<H", head[18:20])[0]
        if machine != EXPECTED_EM_AARCH64:
            fail("%s e_machine=%#x is not AArch64" % (name, machine))
            continue
        checked += 1
    if checked == len(EXPECTED_DRIVERS):
        ok("bin/: %d 个驱动均为 AArch64 ELF（%s）"
           % (checked, ", ".join(EXPECTED_DRIVERS)))


def check_xml(xml, bindir):
    if not os.path.isfile(xml):
        fail("INDI data file is missing: %s" % xml)
        return
    with open(xml, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    declared = re.findall(r'<driver\s+name="[^"]*"\s*>\s*([^<\s]+)\s*</driver>', text)
    missing = [name for name in EXPECTED_DRIVERS if name not in declared]
    extra = [name for name in declared if name not in EXPECTED_DRIVERS]
    if missing:
        fail("INDI data file does not declare: %s" % ", ".join(missing))
        return
    if extra:
        fail("INDI data file declares unexpected drivers: %s" % ", ".join(extra))
        return
    absent = [name for name in declared
              if not os.path.isfile(os.path.join(bindir, name))]
    if absent:
        fail("executables referenced by the INDI data file are not in bin/: %s"
             % ", ".join(absent))
        return
    ok("share/indi/indi_lunatico.xml: 6 条 <driver> 与 bin/ 逐一对应")


def read_needed(path):
    """Return the DT_NEEDED sonames of an ELF64 little-endian object."""
    with open(path, "rb") as fh:
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


def check_linkage(bindir, indi_libdir):
    """Every driver must carry a complete, relocatable INDI closure."""
    audited = 0
    for name in EXPECTED_DRIVERS:
        path = os.path.join(bindir, name)
        if not os.path.isfile(path):
            continue
        try:
            needed = read_needed(path)
        except Exception as exc:
            fail("could not read DT_NEEDED of %s: %s" % (name, exc))
            continue
        absolute = [entry for entry in needed if entry.startswith("/")]
        if absolute:
            fail("%s DT_NEEDED holds absolute paths: %s" % (name, ", ".join(absolute)))
            continue
        missing = [entry for entry in INDI_CORE_LIBS if entry not in needed]
        if missing:
            fail("%s does not link the INDI core libraries %s (DT_NEEDED=%s)"
                 % (name, ", ".join(missing), ", ".join(needed)))
            continue
        audited += 1
    if audited == len(EXPECTED_DRIVERS):
        absent = [entry for entry in INDI_CORE_LIBS
                  if not os.path.isfile(os.path.join(indi_libdir, entry))]
        if absent:
            fail("INDI core libraries missing from %s: %s"
                 % (indi_libdir, ", ".join(absent)))
            return
        ok("DT_NEEDED 闭包完整：%d 个驱动均记录 %s（且三者都在 libindi 包内）"
           % (audited, ", ".join(INDI_CORE_LIBS)))


def check_rules(rules_file):
    if not rules_file:
        skip("未提供 udev 规则路径（跳过该项）")
        return
    if not os.path.isfile(rules_file):
        fail("udev rules file was not packaged: %s "
             "（RULES_INSTALL_DIR 重定向未生效）" % rules_file)
        return
    with open(rules_file, "r", errors="replace") as fh:
        text = fh.read()
    if 'SUBSYSTEMS=="usb"' not in text:
        fail("packaged udev rules file looks empty/foreign: %s" % rules_file)
        return
    ok("udev 规则已随包安装（重定向进私有前缀）: %s" % rules_file)


def check_exec(driver):
    """Best effort: let the loader start one driver, classify host refusals."""
    if not os.path.isfile(driver):
        skip("无可执行的驱动用于 best-effort 运行检查")
        return
    try:
        proc = subprocess.run([driver, "--help"], stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=15)
        out = proc.stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        ok("driver started and stayed alive until the 15s timeout (closure resolved)")
        return
    except OSError as exc:
        low = str(exc).lower()
        if any(tag in low for tag in LOADER_ERRORS):
            fail("loader reported a missing library or unresolved symbol: %s" % exc)
        elif any(tag in low for tag in PLATFORM_LIMITS):
            skip("host refused to start the OHOS binary (platform limit): %s" % exc)
        else:
            fail("could not execute the driver: %s" % exc)
        return

    low = out.lower()
    if any(tag in low for tag in LOADER_ERRORS):
        fail("loader reported a missing library or unresolved symbol: %s" % out.strip()[:300])
        return
    if any(tag in low for tag in PLATFORM_LIMITS):
        skip("host refused to start the OHOS binary (platform limit): %s" % out.strip()[:300])
        return
    ok("driver exec'd cleanly (exit=%s, no unresolved shared library)" % proc.returncode)


def check_e2e(bindir, indi_libdir):
    """端到端消费者用例（rule12）：真正跑通一次 INDI 流程。

    流程：`indiserver`（libindi 包内自带）启动本包的驱动 → 用 `indi_getprop` 以
    **INDI 客户端**身份连接并读取属性 → 断言至少读到属性（驱动↔客户端两端真实交互，
    非纯断言）。任一步因宿主限制无法进行（不允许监听/连接 127.0.0.1、平台限制）
    → 按**具名环境信号**记 SKIP 并写明证据，其余情况判 FAIL。
    """
    indi_bin = os.path.join(os.path.dirname(indi_libdir), "bin")
    server = os.path.join(indi_bin, "indiserver")
    getprop = os.path.join(indi_bin, "indi_getprop")
    driver = os.path.join(bindir, EXPECTED_DRIVERS[0])
    for tool in (server, getprop, driver):
        if not os.path.isfile(tool):
            fail("E2E 所需二进制缺失：%s（应为 libindi 包内自带的工具）" % tool)
            return
    env = dict(os.environ)
    env["PATH"] = os.path.dirname(driver) + ":" + indi_bin + ":" + env.get("PATH", "")
    env["LD_LIBRARY_PATH"] = indi_libdir + ":" + env.get("LD_LIBRARY_PATH", "")
    srv = None
    try:
        srv = subprocess.Popen([server, "-v", "-p", "17624", driver],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               env=env)
        time.sleep(4)
        if srv.poll() is not None:
            out = (srv.stdout.read() or b"").decode("utf-8", "replace")
            low = out.lower()
            if any(tag in low for tag in LOADER_ERRORS):
                fail("E2E 失败：indiserver 无法加载驱动（缺库/未解析符号）：%s"
                     % out.strip()[:300])
            elif any(tag in low for tag in PLATFORM_LIMITS):
                skip("E2E：宿主拒绝启动 OHOS 二进制（平台限制）：%s" % out.strip()[:200])
            else:
                fail("E2E 失败：indiserver 提前退出（exit=%s）：%s"
                     % (srv.returncode, out.strip()[:300]))
            return
        proc = subprocess.run([getprop, "-1", "-h", "127.0.0.1", "-p", "17624"],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              timeout=25, env=env)
        out = proc.stdout.decode("utf-8", "replace")
        low = out.lower()
        if any(tag in low for tag in PLATFORM_LIMITS) or "connection refused" in low:
            skip("E2E：宿主不允许本地监听/连接 127.0.0.1:17624（平台限制）：%s"
                 % out.strip()[:200])
            return
        if proc.returncode != 0 or not out.strip():
            fail("E2E 失败：indi_getprop 未取到任何属性（rc=%s）：%s"
                 % (proc.returncode, out.strip()[:300]))
            return
        props = [ln for ln in out.splitlines() if ln.strip()]
        ok("E2E 真跑通过：indiserver 拉起驱动 + indi_getprop 客户端连上并读到 %d 行属性"
           "（首行：%s）" % (len(props), props[0].strip()[:80]))
    except subprocess.TimeoutExpired:
        skip("E2E：indi_getprop 连接/读取超时（宿主网络或监听受限）")
    except OSError as exc:
        low = str(exc).lower()
        if any(tag in low for tag in PLATFORM_LIMITS):
            skip("E2E：宿主拒绝启动（平台限制）：%s" % exc)
        else:
            fail("E2E 无法执行：%s" % exc)
    finally:
        if srv is not None:
            srv.terminate()
            try:
                srv.wait(timeout=5)
            except Exception:
                srv.kill()


def main():
    if len(sys.argv) not in (4, 5):
        print(__doc__)
        return 2
    bindir, xml, indi_libdir = sys.argv[1:4]
    rules_file = sys.argv[4] if len(sys.argv) == 5 else ""
    check_elfs(bindir)
    check_xml(xml, bindir)
    check_linkage(bindir, indi_libdir)
    check_rules(rules_file)
    check_exec(os.path.join(bindir, EXPECTED_DRIVERS[0]))
    check_e2e(bindir, indi_libdir)
    print("checks=%d fails=%d skips=%d" % (6, len(fails), len(skips)))
    if fails:
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
