#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_layout.py — ebtables 2.0.11 交付形态自检（M 项）

纯 Python（自解析 ELF，不依赖 readelf/objdump/nm——OHOS worker 上这些工具未必存在）。
每项检查的来源都是包内真实文件、conan 生成物或消费端二进制的动态段；没有恒真断言。
"""
import argparse
import os
import struct
import sys

FAILURES = []
CHECKS = []
SKIPS = []

# ELF e_machine
ELF_MACHINE = {"armv8": 183, "x86_64": 62, "x86": 3}

# 上游 Makefile.am 的 sbin_PROGRAMS / sbin_SCRIPTS（安装到 bin/）
PROGRAMS = ("ebtables-legacy", "ebtablesd", "ebtablesu", "ebtables-legacy-restore")
SCRIPTS = ("ebtables-legacy-save",)
# 上游 include/ 树（配方安装；Makefile.am 没有 include_HEADERS）
HEADERS = (
    "ebtables_u.h",
    "ethernetdb.h",
    "linux/types.h",
    "linux/netfilter_bridge.h",
    "linux/netfilter/xt_AUDIT.h",
    "linux/netfilter_bridge/ebtables.h",
    "linux/netfilter_bridge/ebt_802_3.h",
    "linux/netfilter_bridge/ebt_among.h",
    "linux/netfilter_bridge/ebt_arp.h",
    "linux/netfilter_bridge/ebt_arpreply.h",
    "linux/netfilter_bridge/ebt_ip.h",
    "linux/netfilter_bridge/ebt_ip6.h",
    "linux/netfilter_bridge/ebt_limit.h",
    "linux/netfilter_bridge/ebt_log.h",
    "linux/netfilter_bridge/ebt_mark_m.h",
    "linux/netfilter_bridge/ebt_mark_t.h",
    "linux/netfilter_bridge/ebt_nat.h",
    "linux/netfilter_bridge/ebt_nflog.h",
    "linux/netfilter_bridge/ebt_pkttype.h",
    "linux/netfilter_bridge/ebt_redirect.h",
    "linux/netfilter_bridge/ebt_stp.h",
    "linux/netfilter_bridge/ebt_ulog.h",
    "linux/netfilter_bridge/ebt_vlan.h",
)


def record(name, ok, detail):
    CHECKS.append((name, bool(ok), detail))
    if not ok:
        FAILURES.append(name)


def skip(name, detail):
    SKIPS.append((name, detail))
    print("  [skip] {} — {}".format(name, detail))


def read_text(path):
    if not os.path.isfile(path):
        return ""
    with open(path, "r", errors="replace") as fh:
        return fh.read()


def elf_info(path):
    with open(path, "rb") as fh:
        data = fh.read()
    info = {"elf": data[:4] == b"\x7fELF", "class": data[4] if len(data) > 4 else 0,
            "endian": data[5] if len(data) > 5 else 0, "type": None, "machine": None,
            "soname": None, "needed": [], "codesign": b".codesign" in data}
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
        if p_type == 1:                                  # PT_LOAD
            p_offset, p_vaddr, _p_paddr, p_filesz = struct.unpack_from("<QQQQ", data, off + 8)
            loads.append((p_vaddr, p_offset, p_filesz))
        elif p_type == 2:                                # PT_DYNAMIC
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

    def vaddr_to_off(v):
        for p_vaddr, p_offset, p_filesz in loads:
            if p_vaddr <= v < p_vaddr + p_filesz:
                return p_offset + (v - p_vaddr)
        return None

    if strtab is not None:
        for tag, val in entries:
            if tag not in (1, 14):                       # DT_NEEDED / DT_SONAME
                continue
            off = vaddr_to_off(strtab + val)
            if off is None:
                continue
            end = data.index(b"\x00", off)
            text = data[off:end].decode("utf-8", "replace")
            if tag == 14:
                info["soname"] = text
            else:
                info["needed"].append(text)
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package-folder", required=True)
    ap.add_argument("--os", required=True)
    ap.add_argument("--arch", required=True)
    ap.add_argument("--version", required=True)
    ap.add_argument("--generators-dir", required=True)
    ap.add_argument("--build-dir", required=True)
    a = ap.parse_args()

    pkg = a.package_folder
    libdir = os.path.join(pkg, "lib")
    bindir = os.path.join(pkg, "bin")
    incdir = os.path.join(pkg, "include")
    want_machine = ELF_MACHINE.get(a.arch)
    is_ohos = a.os == "OHOS"

    # ── M1 lib/ = 交付的 libebtc soname 链，且无 .la ────────────────────
    libs = sorted(os.listdir(libdir)) if os.path.isdir(libdir) else []
    expected = {"libebtc.so", "libebtc.so.0", "libebtc.so.0.0.0"}
    junk_la = [n for n in libs if n.endswith(".la")]
    record("M1 lib/ = libebtc.so{,.0,.0.0.0} only, no libtool archive",
           os.path.isdir(libdir) and set(libs) == expected and not junk_la,
           "lib/={} junk={}".format(libs, junk_la))

    # ── M2/M3 真实库：ELF64 ET_DYN、架构匹配、DT_SONAME ───────────────
    real = os.path.join(libdir, "libebtc.so.0.0.0")
    info = elf_info(real) if os.path.isfile(real) else {}
    record("M2 libebtc.so.0.0.0 is ELF64 ET_DYN for arch {} (e_machine={})".format(
        a.arch, want_machine),
           bool(info) and info.get("elf") and info.get("class") == 2
           and info.get("endian") == 1 and info.get("type") == 3
           and (want_machine is None or info.get("machine") == want_machine),
           "type={} machine={}".format(info.get("type"), info.get("machine")))
    record("M3 libebtc.so.0.0.0 DT_SONAME == libebtc.so.0",
           info.get("soname") == "libebtc.so.0", str(info.get("soname")))

    # ── M4 soname 软链链可解析（无悬空、相对链接）─────────────────────
    chain, bad_links = [], []
    for name in ("libebtc.so", "libebtc.so.0"):
        path = os.path.join(libdir, name)
        if os.path.islink(path):
            target = os.readlink(path)
            chain.append("{}->{}".format(name, target))
            if os.path.isabs(target) or os.path.realpath(path) != os.path.realpath(real):
                bad_links.append(name)
        else:
            bad_links.append(name + "(not a symlink)")
    record("M4 libebtc.so -> libebtc.so.0 -> libebtc.so.0.0.0 resolvable relative links",
           not bad_links and len(chain) == 2, "chain={} bad={}".format(chain, bad_links))

    # ── M5 bin/ 交付物集合 + 无悬空/绝对软链 ───────────────────────────
    bins = sorted(os.listdir(bindir)) if os.path.isdir(bindir) else []
    want_bins = sorted(PROGRAMS + SCRIPTS)
    dangling = [n for n in bins
                if os.path.islink(os.path.join(bindir, n))
                and not os.path.exists(os.path.join(bindir, n))]
    absolute = [n for n in bins
                if os.path.islink(os.path.join(bindir, n))
                and os.path.isabs(os.readlink(os.path.join(bindir, n)))]
    record("M5 bin/ = upstream sbin_PROGRAMS + sbin_SCRIPTS, no dangling/absolute links",
           bins == want_bins and not dangling and not absolute,
           "bin/={} dangling={} absolute={}".format(bins, dangling, absolute))

    # ── M6 可执行文件是 ELF 且架构匹配；DT_NEEDED 契约 ─────────────────
    prog_info = {}
    bad_prog = []
    for name in PROGRAMS:
        path = os.path.join(bindir, name)
        i = elf_info(path) if os.path.isfile(path) else {}
        prog_info[name] = i
        if not (i.get("elf") and i.get("class") == 2
                and (want_machine is None or i.get("machine") == want_machine)):
            bad_prog.append(name)
    record("M6 the 4 sbin_PROGRAMS are ELF64 of arch {} (script is not ELF)".format(a.arch),
           len(PROGRAMS) == 4 and not bad_prog, "bad={}".format(bad_prog))
    needs_libebtc = {n: "libebtc.so.0" in prog_info[n].get("needed", []) for n in PROGRAMS}
    record("M6b ebtables-legacy/ebtablesd/ebtables-legacy-restore DT_NEEDED libebtc.so.0 "
           "(ebtablesu is linked standalone by upstream: no libebtc)",
           needs_libebtc["ebtables-legacy"] and needs_libebtc["ebtablesd"]
           and needs_libebtc["ebtables-legacy-restore"] and not needs_libebtc["ebtablesu"],
           "needed={}".format({n: prog_info[n].get("needed", []) for n in PROGRAMS}))

    # ── M7 ebtables-legacy-save 是上游 perl 脚本（@sbindir@ 已替换）────
    save = os.path.join(bindir, "ebtables-legacy-save")
    save_text = read_text(save)
    record('M7 ebtables-legacy-save keeps the upstream perl shebang and the '
           'substituted sbindir ("/bin/ebtables")',
           save_text.startswith("#!/usr/bin/perl -w")
           and '"/bin/ebtables"' in save_text
           and "Generated by ebtables-save v$version (legacy)" in save_text,
           "first line={!r}".format(save_text.splitlines()[0] if save_text else ""))

    # ── M8 头文件闭包 + 公共声明 ──────────────────────────────────────
    missing = [h for h in HEADERS if not os.path.isfile(os.path.join(incdir, h))]
    u_h = read_text(os.path.join(incdir, "ebtables_u.h"))
    edb_h = read_text(os.path.join(incdir, "ethernetdb.h"))
    record("M8 include closure ({} headers) + public API declarations".format(len(HEADERS)),
           not missing and "do_command" in u_h and "ebt_find_match" in u_h
           and "ebt_parse_ip_address" in u_h and "getethertypebyname" in edb_h,
           "missing={}".format(missing))

    # ── M9 ethertypes 数据文件（IANA 行）──────────────────────────────
    eth = os.path.join(pkg, "etc", "ethertypes")
    eth_text = read_text(eth)
    ipv4_ok = any(ln.split()[0] == "IPv4" and ln.split()[1].lower() == "0800"
                  for ln in eth_text.splitlines()
                  if ln.strip() and not ln.lstrip().startswith("#") and len(ln.split()) > 1)
    arp_ok = any(ln.split()[0] == "ARP" and ln.split()[1].lower() == "0806"
                 for ln in eth_text.splitlines()
                 if ln.strip() and not ln.lstrip().startswith("#") and len(ln.split()) > 1)
    record("M9 etc/ethertypes present with the IANA rows (IPv4 0800 / ARP 0806)",
           ipv4_ok and arp_ok, "{} bytes, ipv4={} arp={}".format(len(eth_text), ipv4_ok, arp_ok))

    # ── M10 man 页（版本号由上游 sed 从 @PACKAGE_VERSION@ 替换而来）────
    man = read_text(os.path.join(pkg, "share", "man", "man8", "ebtables-legacy.8"))
    record("M10 share/man/man8/ebtables-legacy.8 carries the version {}".format(a.version),
           man.startswith(".TH EBTABLES 8") and ("(" + a.version) in man,
           "{} bytes".format(len(man)))

    # ── M11 GPL 原文 ──────────────────────────────────────────────────
    lic = read_text(os.path.join(pkg, "licenses", "COPYING"))
    record("M11 licenses/COPYING is the upstream GPL-2.0 text",
           "GNU GENERAL PUBLIC LICENSE" in lic and "Version 2" in lic,
           os.path.join(pkg, "licenses", "COPYING"))

    # ── M12 无中间产物 / 无 libtool 残留 ──────────────────────────────
    junk = []
    for root, dirs, files in os.walk(pkg):
        for n in files:
            if n.endswith((".la", ".o", ".a", ".lo", ".pyc")) or n == "conanbuild.sh":
                junk.append(os.path.relpath(os.path.join(root, n), pkg))
        for n in list(dirs):
            if n == "__pycache__":
                junk.append(os.path.relpath(os.path.join(root, n), pkg))
    record("M12 no libtool archives / objects / python caches / conan build scripts",
           not junk, "junk={}".format(junk[:5]))

    # ── M13 无隐藏文件（JC5）──────────────────────────────────────────
    hidden = []
    for root, dirs, files in os.walk(pkg):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for n in list(files) + list(dirs):
            if n.startswith("."):
                hidden.append(os.path.relpath(os.path.join(root, n), pkg))
    record("M13 no hidden files in the package (JC5)", not hidden,
           "hidden={}".format(hidden[:5]))

    # ── M14 CMakeDeps 契约 ────────────────────────────────────────────
    gen = a.generators_dir
    cmake_text, cmake_files = "", []
    for root, _dirs, files in os.walk(gen):
        for n in files:
            if n.endswith(".cmake"):
                cmake_files.append(n)
                cmake_text += read_text(os.path.join(root, n)) + "\n"
    record("M14 CMakeDeps contract: ebtables-config.cmake defines ebtables::ebtables",
           os.path.isfile(os.path.join(gen, "ebtables-config.cmake"))
           and "ebtables::ebtables" in cmake_text and "ebtc" in cmake_text,
           "cmake files={}".format(sorted(set(cmake_files))[:6]))

    # ── M15 pkg-config 契约可重定位 ───────────────────────────────────
    pc_files = []
    for root, _dirs, files in os.walk(gen):
        pc_files += [os.path.join(root, n) for n in files if n.endswith(".pc")]
    pc_text = "".join(read_text(p) for p in pc_files)
    nonreloc = []
    for ln in pc_text.splitlines():
        if not ln.startswith(("libdir=", "includedir=")):
            continue
        value = ln.split("=", 1)[1]
        if "${prefix}" in value or not value.startswith("/"):
            continue
        nonreloc.append(ln)
    has_pc = any(os.path.basename(p) == "ebtables.pc" for p in pc_files)
    record("M15 PkgConfigDeps contract: ebtables.pc generated + relocatable via ${prefix}",
           has_pc and "-lebtc" in pc_text and not nonreloc,
           "pc={} nonreloc={}".format(sorted({os.path.basename(p) for p in pc_files}), nonreloc))

    # ── M16 消费者二进制的 DT_NEEDED（真实链接证据）───────────────────
    consumer = None
    for root, _dirs, files in os.walk(a.build_dir):
        if "generators" in root:
            continue
        for n in files:
            if n == "test_ebtables":
                consumer = os.path.join(root, n)
    needed = elf_info(consumer)["needed"] if consumer else []
    record("M16 consumer binary DT_NEEDED contains libebtc.so.0 (real link)",
           consumer is not None and "libebtc.so.0" in needed,
           "consumer={} needed={}".format(consumer, needed))

    # ── M17 OHOS 签名段 ──────────────────────────────────────────────
    sos = [os.path.join(libdir, n) for n in libs if n.endswith(".so.0.0.0")]
    if is_ohos:
        unsigned = [os.path.basename(p) for p in sos if not elf_info(p)["codesign"]]
        record("M17 the delivered .so carries a .codesign section ({} file(s))".format(len(sos)),
               bool(sos) and not unsigned, "unsigned={}".format(unsigned))
    else:
        skip("M17 .codesign section check",
             "not an OHOS build ({}); signing runs only for os=OHOS and is checked "
             "for real on the OHOS CI worker".format(a.os))

    # ── 结果 ──────────────────────────────────────────────────────────
    for name, ok, detail in CHECKS:
        print("  [{}] {}  ({})".format("ok" if ok else "FAIL", name, detail))
    print("\n交付形态自检：{} 项通过 / {} 项失败 / {} 项跳过（共 {} 项）".format(
        len(CHECKS) - len(FAILURES), len(FAILURES), len(SKIPS), len(CHECKS) + len(SKIPS)))
    for name, detail in SKIPS:
        print("  跳过：{} —— {}".format(name, detail))
    if FAILURES:
        print("失败项：" + ", ".join(FAILURES))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
