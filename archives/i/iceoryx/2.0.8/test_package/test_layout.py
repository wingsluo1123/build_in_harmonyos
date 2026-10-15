#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_layout.py — iceoryx 2.0.8 交付形态自检（M 项）

纯 Python（自解析 ELF）。每项检查都有明确来源：包内真实文件、上游安装的 CMake
配置、CMakeDeps/PkgConfigDeps 生成物、或消费端二进制的动态段。无恒真断言。
"""
import argparse
import os
import struct
import sys

FAILURES = []
CHECKS = []
SKIPS = []

ELF_MACHINE = {"armv8": 183, "x86_64": 62, "x86": 3}

# 本包声明的交付库（与 upstream make install 的结论一致；不含 *_testing.a，
# 也不含 TOML_CONFIG=OFF 下不存在 的 iceoryx_posh_config / iox-roudi）
EXPECTED_LIBS = ["libiceoryx_binding_c.so", "libiceoryx_hoofs.so",
                 "libiceoryx_platform.so", "libiceoryx_posh.so",
                 "libiceoryx_posh_gateway.so", "libiceoryx_posh_roudi.so"]


def record(name, ok, detail):
    CHECKS.append((name, bool(ok), detail))
    if not ok:
        FAILURES.append(name)


def skip(name, detail):
    SKIPS.append((name, detail))
    print("  [skip] {} — {}".format(name, detail))


def elf_info(path):
    with open(path, "rb") as fh:
        data = fh.read()
    info = {"elf": data[:4] == b"\x7fELF", "class": data[4], "endian": data[5],
            "type": None, "machine": None, "soname": None, "needed": [],
            "rpaths": [], "codesign": b".codesign" in data}
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
        if p_type == 1:                      # PT_LOAD
            p_offset, p_vaddr, _p_paddr, p_filesz = struct.unpack_from("<QQQQ", data, off + 8)
            loads.append((p_vaddr, p_offset, p_filesz))
        elif p_type == 2:                    # PT_DYNAMIC
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
            if tag not in (1, 14, 15, 29):   # NEEDED / SONAME / RPATH / RUNPATH
                continue
            off = vaddr_to_off(strtab + val)
            if off is None:
                continue
            end = data.index(b"\x00", off)
            text = data[off:end].decode("utf-8", "replace")
            if tag == 14:
                info["soname"] = text
            elif tag == 1:
                info["needed"].append(text)
            else:
                info["rpaths"].append(text)
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
    incdir = os.path.join(pkg, "include")
    want_machine = ELF_MACHINE.get(a.arch)
    is_ohos = a.os == "OHOS"

    infos = {}
    for name in EXPECTED_LIBS:
        path = os.path.join(libdir, name)
        infos[name] = elf_info(path) if os.path.isfile(path) else None

    # ── C1 交付库集合（无测试库、无 benchmark）─────────────────────────
    libs = sorted(n for n in os.listdir(libdir)
                  if n.endswith((".so", ".a"))) if os.path.isdir(libdir) else []
    record("C1 lib/ = exactly the 6 delivered libraries, no *_testing.a",
           libs == EXPECTED_LIBS, "lib/={}".format(libs))

    # ── C2 全部为 ELF64/ET_DYN 且架构匹配 settings.arch ────────────────
    bad = [n for n, i in infos.items()
           if not i or not i["elf"] or i["class"] != 2 or i["type"] != 3
           or (want_machine is not None and i["machine"] != want_machine)]
    record("C2 all 6 libraries are ELF64 ET_DYN of arch {} (e_machine={})".format(
               a.arch, want_machine), not bad, "bad={}".format(bad))

    # ── C3 DT_SONAME（OHOS 无 Platform/HarmonyOS.cmake ⇒ 必须显式兜底）──
    nosoname = [n for n, i in infos.items() if not i or i["soname"] != n]
    record("C3 every library carries DT_SONAME == its own file name "
           "(no Platform/HarmonyOS.cmake fallback needed)", not nosoname,
           "missing/odd soname={}".format(
               {n: (i or {}).get("soname") for n in nosoname}))

    # ── C4 动态段无 RPATH/RUNPATH（可重定位）──────────────────────────
    rpaths = {n: (i or {}).get("rpaths") for n, i in infos.items()
              if (i or {}).get("rpaths")}
    record("C4 no delivered library carries DT_RPATH/DT_RUNPATH (relocatable)",
           not rpaths, "rpaths={}".format(rpaths))
    # Informational: upstream's IOX_ASSERT/IOX_LOG embed __FILE__ in .rodata,
    # so the build-time source path appears as a string.  It is not a dynamic
    # loader path and does not affect relocation.
    with open(os.path.join(libdir, EXPECTED_LIBS[1]), "rb") as fh:
        blob = fh.read()
    if b".conan2" in blob or b"/home/" in blob:
        print("  [info] libiceoryx_hoofs.so embeds build-time __FILE__ paths "
              "(upstream IOX_ASSERT/IOX_LOG) - informational, no DT_RPATH effect")

    # ── C5 库间 DT_NEEDED 链完整 ──────────────────────────────────────
    chain = {
        "libiceoryx_hoofs.so": "libiceoryx_platform.so",
        "libiceoryx_posh.so": "libiceoryx_hoofs.so",
        "libiceoryx_binding_c.so": "libiceoryx_posh.so",
    }
    broken = {n: need for n, need in chain.items()
              if need not in (infos.get(n) or {}).get("needed", [])}
    record("C5 DT_NEEDED chain binding_c -> posh -> hoofs -> platform is complete",
           not broken, "broken={}".format(broken))

    # ── C6 OHOS 签名段 ────────────────────────────────────────────────
    if is_ohos:
        unsigned = [n for n, i in infos.items() if not i.get("codesign")]
        record("C6 every delivered .so carries a .codesign section ({} files)".format(
                   len(EXPECTED_LIBS)), not unsigned, "unsigned={}".format(unsigned))
    else:
        skip("C6 .codesign section check",
             "not an OHOS build ({}); signing runs only for os=OHOS, the check is "
             "executed for real on the OHOS CI worker".format(a.os))

    # ── C7 公共头闭包 ─────────────────────────────────────────────────
    subdirs = ["iceoryx_hoofs", "iceoryx_posh", "iceoryx_binding_c"]
    verdir = os.path.join(incdir, "iceoryx", "v{}".format(a.version))
    counts = {}
    for sub in subdirs:
        base = os.path.join(verdir, sub)
        counts[sub] = sum(1 for _r, _d, fs in os.walk(base) for f in fs
                          if f.endswith((".hpp", ".h"))) if os.path.isdir(base) else 0
    runtime_h = os.path.join(verdir, "iceoryx_binding_c", "runtime.h")
    decls = ""
    if os.path.isfile(runtime_h):
        with open(runtime_h, "r", errors="replace") as fh:
            decls = fh.read()
    record("C7 public headers installed under include/iceoryx/v{}/ ({})".format(
               a.version, counts),
           all(v > 20 for v in counts.values()) and "iox_runtime_init" in decls,
           "counts={} runtime.h={}".format(counts, bool(decls)))

    # ── C8 许可 ───────────────────────────────────────────────────────
    lic = os.path.join(pkg, "licenses", "LICENSE")
    notice = os.path.join(pkg, "licenses", "NOTICE.md")
    lic_ok = False
    if os.path.isfile(lic):
        with open(lic, "r", errors="replace") as fh:
            text = fh.read()
        lic_ok = "Apache License" in text and "Version 2.0" in text
    record("C8 licenses/ carries the Apache-2.0 text and upstream NOTICE.md",
           lic_ok and os.path.isfile(notice), lic)

    # ── C9 无测试产物 / 中间产物 ─────────────────────────────────────
    junk = []
    for root, dirs, files in os.walk(pkg):
        for n in files:
            if (n.endswith(("_testing.a", ".la", ".o", ".pyc"))
                    or n.startswith("iox-bm-")):
                junk.append(n)
        for d in dirs:
            if d == "__pycache__" or (d == "googletest" and "/lib/cmake" in root):
                junk.append(os.path.relpath(os.path.join(root, d), pkg))
    record("C9 no test libraries / benchmarks / libtool archives / caches in the package",
           not junk, "junk={}".format(junk[:6]))

    # ── C10 无隐藏文件（JC5）──────────────────────────────────────────
    hidden = []
    for root, dirs, files in os.walk(pkg):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for n in files + dirs:
            if n.startswith("."):
                hidden.append(os.path.relpath(os.path.join(root, n), pkg))
    record("C10 no hidden files in the package (JC5)", not hidden,
           "hidden={}".format(hidden[:5]))

    # ── C11 CMake 契约（上游 config + conan 生成物）───────────────────
    gen = a.generators_dir
    up_config = os.path.join(libdir, "cmake", "iceoryx_posh", "iceoryx_poshConfig.cmake")
    ctext = ""
    for root, _dirs, files in os.walk(gen):
        for n in files:
            if n.endswith(".cmake"):
                with open(os.path.join(root, n), "r", errors="replace") as fh:
                    ctext += fh.read() + "\n"
    record("C11 upstream iceoryx_poshConfig.cmake delivered + conan targets generated",
           os.path.isfile(up_config)
           and all(t in ctext for t in ("iceoryx::iceoryx_hoofs",
                                        "iceoryx::iceoryx_posh",
                                        "iceoryx::iceoryx_binding_c")),
           "upstream_config={}".format(os.path.isfile(up_config)))

    # ── C12 pkg-config 契约可重定位 ───────────────────────────────────
    pc_files, pc_text = [], ""
    for root, _dirs, files in os.walk(gen):
        for n in files:
            if n.endswith(".pc"):
                pc_files.append(n)
                with open(os.path.join(root, n), "r", errors="replace") as fh:
                    pc_text += fh.read() + "\n"
    nonreloc = []
    for ln in pc_text.splitlines():
        if not ln.startswith(("libdir=", "includedir=")):
            continue
        value = ln.split("=", 1)[1]
        if "${prefix}" not in value and value.startswith("/"):
            nonreloc.append(ln)
    record("C12 PkgConfigDeps contract: iceoryx_*.pc generated + relocatable",
           "iceoryx.pc" in pc_files and not nonreloc,
           "pc={} nonreloc={}".format(sorted(set(pc_files))[:6], nonreloc))

    # ── C13 消费者二进制的 DT_NEEDED ─────────────────────────────────
    consumer, needed = None, []
    for root, _dirs, files in os.walk(a.build_dir):
        if "generators" in root:
            continue
        if "test_package" in files:
            consumer = os.path.join(root, "test_package")
    if consumer:
        needed = elf_info(consumer)["needed"]
    record("C13 consumer binary DT_NEEDED carries posh + binding_c + hoofs (real link)",
           all(n in needed for n in ("libiceoryx_posh.so",
                                     "libiceoryx_binding_c.so",
                                     "libiceoryx_hoofs.so")),
           "needed={}".format(needed))

    # ── C13b 交付库真的导出消费者要用的 API ───────────────────────────
    def exports(lib, symbols):
        with open(os.path.join(libdir, lib), "rb") as fh:
            data = fh.read()
        return [s for s in symbols if s.encode() not in data]

    missing_syms = (exports("libiceoryx_binding_c.so",
                            ["iox_pub_init", "iox_sub_init", "iox_runtime_init"])
                    + exports("libiceoryx_posh.so", ["_ZN3iox4popo"])
                    + exports("libiceoryx_hoofs.so", ["_ZN3iox3cxx"]))
    record("C13b delivered libraries export the public API used by consumers "
           "(binding_c C ABI + posh/hoofs C++ symbols)", not missing_syms,
           "missing={}".format(missing_syms))

    # ── C14 声明的裁剪确实不存在（负向检查）──────────────────────────
    absent = [n for n in ("iox-roudi",) if os.path.exists(os.path.join(pkg, "bin", n))]
    record("C14 the declared TOML reduction is real: no iox-roudi, no "
           "iceoryx_posh_config in the package",
           not absent
           and not os.path.isfile(os.path.join(libdir, "libiceoryx_posh_config.so")),
           "unexpected={}".format(absent))

    # ── C15 版本一致性 ───────────────────────────────────────────────
    record("C15 installed header tree version dir matches the package version "
           "({})".format(a.version), os.path.isdir(verdir), verdir)

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
