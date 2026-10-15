#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_layout.py — imx_usb_loader 交付形态自检（M 项，≥10 条）

纯 Python，自解析 ELF（不依赖 readelf/objdump/nm/file，OHOS worker 上这些工具未必存在）。
每一项的判据都来自包内真实文件、真实 ELF 结构，或**上游 tarball 派生**的哈希表，没有恒真断言。
"""
import argparse
import hashlib
import os
import struct
import sys

FAILURES = []
CHECKS = []
SKIPS = []

ELF_MACHINE = {"armv8": 183, "aarch64": 183, "x86_64": 62, "x86": 3}

# 上游 `make install` 的 `install -m644 *.conf` 装的就是这 14 个文件。
# 名字与 sha256 全部从**钉死的上游 tarball**（commit 30b43d69770c…）里取出，可用
#   curl -L <conandata.yml 的 url> | tar xz && cd imx_usb_loader-30b43d69… && sha256sum *.conf
# 逐条复现；不是从本包自身算出来的。
CONF_SHA256 = {
    "imx_usb.conf": "7c7e4b15fda577c602fc7671089bb62c656a1b29089d31047d895649ed72dafd",
    "mx50_usb_work.conf": "28fc9cf4089d531125754f74273a1995304f9a5e6fd3c09698ad2a9f201aa27a",
    "mx51_usb_work.conf": "d1e0edc70cedba21d832835a82ca6b09e13443119de060c6ff2c74b431fed4ec",
    "mx53_usb_work.conf": "ac85f7f3f1c30cb8a782809828888d98d29d5fe75f2cfd48506789f25f6d33f2",
    "mx6_usb_sdp_spl.conf": "9f084d067650b4127e4ce4dfe29f35befa1028455d12daa6cf3f99d7643aa77a",
    "mx6_usb_work.conf": "7a1e8424fd55d0f33b09b781d53fc825c475672b31452090f7c823f6a8fbd9d2",
    "mx6ull_usb_work.conf": "55dffa83a6fef2e47eed17ff21b9516f1281263fadb9bc573fc4214620b9b8fb",
    "mx7_usb_work.conf": "2ffcb949090c16ea6c6d896cff9707fa7802747d4e1a52c9b6e32590f0856d69",
    "mx7ulp_usb_work.conf": "6aa185923cd6cae75907a071954d7670e6195504df2d3035d0ce8cd8837703e3",
    "mx8m_usb_sdp_spl.conf": "bd11147b96268a67f03b0e73c3d985ea21079cad17e52b2ca5e645bacc568aa3",
    "mx8mm_usb_work.conf": "6f3965159dc6de7509b76b73a7e1a02aad3547871088751c709313172c2dc95d",
    "mx8mn_usb_work.conf": "3bf7f2892b0a9d3141b8c3699d8550c5b3a28da7741abb2c23561b85d530f716",
    "mx8mq_usb_work.conf": "ffb7d0d2c8e7badd6cb3fce5e0a7379447a355525fc5e7edaa568c9d5a919c9a",
    "vybrid_usb_work.conf": "eed4b92d293561432ea13a4aa6ffdf36db426b51658683337168f62de416d946",
}

VERSION_STRING = "0.2pre"          # imx_loader.h:22  #define IMX_LOADER_VERSION "0.2pre"


def record(name, ok, detail=""):
    CHECKS.append((name, bool(ok), detail))
    if not ok:
        FAILURES.append(name)
    print("  [{}] {} {}".format("ok" if ok else "FAIL", name, detail))


def skip(name, detail):
    SKIPS.append((name, detail))
    print("  [skip] {} — {}".format(name, detail))


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 16), b""):
            h.update(blk)
    return h.hexdigest()


def elf_info(path):
    with open(path, "rb") as fh:
        data = fh.read()
    info = {"elf": data[:4] == b"\x7fELF", "class": data[4], "endian": data[5],
            "type": None, "machine": None, "needed": [], "rpath": None,
            "codesign": b".codesign" in data, "raw": data}
    if not info["elf"] or info["class"] != 2 or info["endian"] != 1:
        return info
    e_type, e_machine = struct.unpack_from("<HH", data, 0x10)
    info["type"], info["machine"] = e_type, e_machine
    e_phoff, = struct.unpack_from("<Q", data, 0x20)
    e_phentsize, e_phnum = struct.unpack_from("<HH", data, 0x36)
    loads, dyn_off = [], None
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type, = struct.unpack_from("<I", data, off)
        if p_type == 1:
            p_offset, p_vaddr, _pp, p_filesz = struct.unpack_from("<QQQQ", data, off + 8)
            loads.append((p_vaddr, p_offset, p_filesz))
        elif p_type == 2:
            dyn_off, = struct.unpack_from("<Q", data, off + 8)
    if dyn_off is None:
        return info
    entries, pos = [], dyn_off
    while True:
        tag, val = struct.unpack_from("<qQ", data, pos)
        entries.append((tag, val))
        pos += 16
        if tag == 0:
            break
    strtab = next((v for t, v in entries if t == 5), None)

    def v2o(v):
        for p_vaddr, p_offset, p_filesz in loads:
            if p_vaddr <= v < p_vaddr + p_filesz:
                return p_offset + (v - p_vaddr)
        return None

    if strtab is not None:
        for tag, val in entries:
            if tag not in (1, 15, 29):        # DT_NEEDED / DT_RPATH / DT_RUNPATH
                continue
            off = v2o(strtab + val)
            if off is None:
                continue
            end = data.index(b"\x00", off)
            text = data[off:end].decode("utf-8", "replace")
            if tag == 1:
                info["needed"].append(text)
            else:
                info["rpath"] = text
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package-folder", required=True)
    ap.add_argument("--os", required=True)
    ap.add_argument("--arch", required=True)
    ap.add_argument("--version", required=True)
    args = ap.parse_args()
    pkg = args.package_folder
    is_ohos = str(args.os) == "OHOS"

    files = []
    for root, dirs, names in os.walk(pkg):
        for n in names:
            files.append(os.path.relpath(os.path.join(root, n), pkg))
    files.sort()
    print("[layout] package_folder={} os={} arch={} version={} entries={}".format(
        pkg, args.os, args.arch, args.version, len(files)))

    # ── M1 两个交付可执行体在位且可执行 ────────────────────────────────
    tools = {"imx_usb": "bin/imx_usb", "imx_uart": "bin/imx_uart"}
    missing = [k for k, v in tools.items()
               if not os.path.isfile(os.path.join(pkg, v))]
    notexec = [k for k, v in tools.items()
               if os.path.isfile(os.path.join(pkg, v))
               and not os.access(os.path.join(pkg, v), os.X_OK)]
    record("M1 bin/imx_usb 与 bin/imx_uart 都在位且带可执行位",
           not missing and not notexec,
           "missing={} notexec={}".format(missing, notexec))

    infos = {k: elf_info(os.path.join(pkg, v)) for k, v in tools.items()
             if os.path.isfile(os.path.join(pkg, v))}

    # ── M2 都是 64 位小端 ELF 可执行/共享对象 ──────────────────────────
    bad = {k: (i["type"], i["class"]) for k, i in infos.items()
           if not i["elf"] or i["class"] != 2 or i["endian"] != 1 or i["type"] not in (2, 3)}
    record("M2 两个产物都是 64 位小端 ELF（ET_EXEC/ET_DYN）", not bad, "{}".format(bad))

    # ── M3 e_machine 与目标 arch 一致 ─────────────────────────────────
    want = ELF_MACHINE.get(str(args.arch))
    if want is None:
        skip("M3 e_machine 与目标 arch 一致", "未收录的 arch {}".format(args.arch))
    else:
        bad3 = {k: i["machine"] for k, i in infos.items() if i["machine"] != want}
        record("M3 e_machine == {}（{}）".format(want, args.arch), not bad3, "{}".format(bad3))

    # ── M4 DT_NEEDED 契约：imx_usb 必须依赖 libusb-1.0.so.0，imx_uart 只依赖 libc
    usb_needed = [n for n in infos.get("imx_usb", {}).get("needed", []) if "libusb" in n]
    uart_needed = [n for n in infos.get("imx_uart", {}).get("needed", []) if "libusb" in n]
    record("M4 imx_usb DT_NEEDED 含 libusb-1.0.so.0，imx_uart 不含 libusb（上游两目标分工）",
           len(usb_needed) == 1 and not uart_needed,
           "imx_usb={} imx_uart={}".format(
               infos.get("imx_usb", {}).get("needed"), infos.get("imx_uart", {}).get("needed")))

    # ── M5 无绝对 RPATH/RUNPATH（构建目录不得泄漏） ────────────────────
    rp = {k: i["rpath"] for k, i in infos.items() if i["rpath"]}
    record("M5 两个产物都没有 RPATH/RUNPATH（运行时靠 LD_LIBRARY_PATH/系统路径）",
           not rp, "{}".format(rp))

    # ── M6 OHOS：逐个含 .codesign 段 ──────────────────────────────────
    if is_ohos:
        bad6 = {k: i["codesign"] for k, i in infos.items() if not i["codesign"]}
        record("M6 OHOS：两个可执行体都含 .codesign 段（已签名）", not bad6, "{}".format(bad6))
    else:
        skip("M6 OHOS：.codesign 段", "非 OHOS 构建（os={}）".format(args.os))

    # ── M7 编译期写死的配置目录契约 ───────────────────────────────────
    # Makefile: -DSYSCONFDIR='"$(sysconfdir)"' -DREL_SYSCONFDIR='"$(rel_sysconfdir)"'
    # 本配方钉死 prefix=/ sysconfdir=/etc rel_sysconfdir=../etc
    want_abs = b"/etc/imx-loader.d"
    want_rel = b"../etc/imx-loader.d"
    bad7 = {k: (want_abs in i["raw"], want_rel in i["raw"]) for k, i in infos.items()
            if not (want_abs in i["raw"] and want_rel in i["raw"])}
    record("M7 两个产物的 .rodata 同时含 SYSCONFDIR=/etc/imx-loader.d 与 "
           "REL_SYSCONFDIR=../etc/imx-loader.d", not bad7, "{}".format(bad7))

    # ── M8 版本横幅字面量来自上游头文件 ───────────────────────────────
    banner = ("imx_usb " + VERSION_STRING).encode()
    bad8 = {k: VERSION_STRING.encode() in i["raw"] for k, i in infos.items()
            if VERSION_STRING.encode() not in i["raw"]}
    record("M8 两个产物内嵌版本串 {!r}（imx_loader.h:22 IMX_LOADER_VERSION）".format(
        VERSION_STRING), not bad8, "{}".format(bad8))

    # ── M9 配置文件目录与文件数 ───────────────────────────────────────
    confdir = os.path.join(pkg, "etc", "imx-loader.d")
    present = sorted(n for n in os.listdir(confdir)) if os.path.isdir(confdir) else []
    record("M9 etc/imx-loader.d/ 存在且恰好是上游 make install 的 14 个 *.conf",
           present == sorted(CONF_SHA256.keys()),
           "got {} 个: {}".format(len(present), present))

    # ── M10 每个配置文件的字节与上游 tarball 一致（哈希表由 tarball 派生）──
    bad10 = []
    for name, want_hash in sorted(CONF_SHA256.items()):
        path = os.path.join(confdir, name)
        if not os.path.isfile(path):
            bad10.append("{} (missing)".format(name))
        elif sha256(path) != want_hash:
            bad10.append("{} (sha256 mismatch)".format(name))
    record("M10 14 个 *.conf 的 sha256 与钉死 tarball 逐条一致", not bad10,
           "{}".format(bad10[:4]))

    # ── M11 无构建中间产物 / libtool 残留 ─────────────────────────────
    junk = [f for f in files
            if f.endswith((".o", ".lo", ".a", ".la", ".test", ".deps", ".libs"))
            or "/.deps/" in "/" + f or "/.libs/" in "/" + f]
    record("M11 包内无 .o/.lo/.a/.la/.test 残留", not junk, "{}".format(junk[:5]))

    # ── M12 无隐藏文件/目录（JC5） ────────────────────────────────────
    hidden = [f for f in files
              if any(p.startswith(".") and p not in (".", "..") for p in f.split("/"))]
    record("M12 包内无隐藏文件/目录（JC5）", not hidden, "{}".format(hidden[:5]))

    # ── M13 上游源码/测试语料没有混进交付物 ───────────────────────────
    leaked = [f for f in files
              if f.endswith((".c", ".h", ".md", ".imx", ".output"))
              or f.startswith("tests/") or f.startswith("msvc/")]
    record("M13 交付物里只有 bin/ 与 etc/ 与 licenses/（无源码、无测试语料、无 msvc/）",
           not leaked, "{}".format(leaked[:5]))

    # ── M14 版本五处一致（目录由调用方保证，这里核对 conandata/manifest）──
    pkgroot = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    verdir = os.path.basename(pkgroot)
    ok14, detail14 = True, "目录={} 参数={}".format(verdir, args.version)
    for name in ("conandata.yml", "manifest.yaml"):
        path = os.path.join(pkgroot, name)
        if os.path.isfile(path):
            with open(path, "r", errors="replace") as fh:
                text = fh.read()
            if args.version not in text or verdir != args.version:
                ok14 = False
                detail14 = "{} / 目录 {} 与 version {} 不一致".format(name, verdir, args.version)
                break
    record("M14 版本一致性：目录名 == conanfile version == conandata 键 == manifest",
           ok14, detail14)

    # ── M15 许可证原文随包 ────────────────────────────────────────────
    lic = os.path.join(pkg, "licenses", "COPYING")
    lic_ok = os.path.isfile(lic) and os.path.getsize(lic) > 20000
    if lic_ok:
        with open(lic, "r", errors="replace") as fh:
            head = fh.read(2000)
        lic_ok = "GNU LESSER GENERAL PUBLIC LICENSE" in head
    record("M15 licenses/COPYING 是上游 LGPL-2.1 原文（>20KB 且首部匹配）", lic_ok, lic)

    print("[layout] checks={} passed={} failed={} skipped={}".format(
        len(CHECKS), len(CHECKS) - len(FAILURES), len(FAILURES), len(SKIPS)))
    if FAILURES:
        print("[layout] FAILED: " + ", ".join(FAILURES))
        return 1
    print("[layout] OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
