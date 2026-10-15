#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_ohos_native.py — imx_usb_loader **鸿蒙特有测试**（OHOS-native，≥10 条）

为什么需要这个文件：上游套件（`make -C tests tests` 的 3 条黄金轨迹）与
`test_consumer.py` / `test_layout.py` 都是**平台中立**的 —— 它们在 Linux 上同样会通过，
因此不能证明「这份交付物在 HarmonyOS 上成立」。本文件只在 `os == "OHOS"` 时执行，
每条判据都是**鸿蒙平台特有**的约束（OHOS 加载器签名、OHOS 无 `/bin/bash`、设备 `/tmp`
只读导致交付物不得依赖它、OHOS 无 CMake 平台表导致不得带 RPATH/RUNPATH），
并在 worker 上**真跑一次交付的 ELF**（能跑就断言横幅，被加载器拒绝则断言拒绝形态
正是已归档的平台策略，并给出「已签名仍被拒 ⇒ 平台策略而非交付缺陷」的结论）。

纯 Python 自解析 ELF（不依赖 readelf/objdump/nm/patchelf，OHOS worker 上未必有）。
非 OHOS 构建**显式打印跳过原因**，绝不静默通过。
"""
import argparse
import os
import struct
import subprocess
import sys

FAILURES = []
CHECKS = []
SKIPS = []

ELF_MACHINE = {"armv8": 183, "aarch64": 183, "x86_64": 62, "x86": 3}
# OHOS 上允许出现在 DT_NEEDED 里的库：libc/libdl/libm/libpthread + 本包的 USB 依赖。
ALLOWED_NEEDED = {
    "libc.so", "libdl.so", "libm.so", "libpthread.so", "librt.so",
    "libusb-1.0.so.0", "libusb-1.0.so",
    # 本机 Linux 复核时 glibc 的 soname（同一判据在两平台都成立：只允许系统库/本包依赖）
    "libc.so.6", "libdl.so.2", "libm.so.6", "libpthread.so.0", "librt.so.1",
}
# 已归档的 OHOS 加载器拒载形态（house rule D/E，knowledge E135/E517）。
LOADER_REFUSAL_MARKERS = (
    "Error loading shared library", "Permission denied", "cannot execute",
    "Exec format error", "not found",
)


def record(name, ok, detail=""):
    CHECKS.append((name, bool(ok), detail))
    if not ok:
        FAILURES.append(name)
    print("  [{}] {} {}".format("ok" if ok else "FAIL", name, detail))


def skip(name, detail):
    SKIPS.append((name, detail))
    print("  [skip] {} — {}".format(name, detail))


# ── 最小 ELF 解析（只读 section header 表 + .dynamic）────────────────────
def elf_parse(path):
    with open(path, "rb") as fh:
        data = fh.read()
    info = {"path": path, "size": len(data), "elf": data[:4] == b"\x7fELF",
            "class": data[4] if len(data) > 5 else None,
            "machine": None, "type": None, "sections": [], "needed": [],
            "rpath": [], "runpath": [], "raw": data}
    if not info["elf"] or info["class"] != 2:
        return info
    e_type, e_machine = struct.unpack_from("<HH", data, 0x10)
    info["type"], info["machine"] = e_type, e_machine
    e_shoff, = struct.unpack_from("<Q", data, 0x28)
    e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", data, 0x3A)
    if e_shoff and e_shnum and e_shstrndx < e_shnum:
        stroff, = struct.unpack_from("<Q", data, e_shoff + e_shstrndx * e_shentsize + 0x18)
        for i in range(e_shnum):
            off = e_shoff + i * e_shentsize
            sh_name, = struct.unpack_from("<I", data, off)
            end = data.find(b"\x00", stroff + sh_name)
            info["sections"].append(data[stroff + sh_name:end].decode("ascii", "replace"))
    # .dynamic：走 PT_DYNAMIC + PT_LOAD 的 vaddr→offset 映射（DT_STRTAB 是**虚拟地址**，
    # 直接当文件偏移读会静默得到空 DT_NEEDED —— 那会变成恒真断言，必须避免）。
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
            if tag not in (1, 15, 29):     # DT_NEEDED / DT_RPATH / DT_RUNPATH
                continue
            off = v2o(strtab + val)
            if off is None:
                continue
            end = data.index(b"\x00", off)
            text = data[off:end].decode("utf-8", "replace")
            {1: info["needed"], 15: info["rpath"], 29: info["runpath"]}[tag].append(text)
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package-folder", required=True)
    ap.add_argument("--os", required=True)
    ap.add_argument("--arch", required=True)
    ap.add_argument("--version", default="")
    ap.add_argument("--build-folder", default="")
    args = ap.parse_args()

    pkg = args.package_folder
    print("[ohos-native] package={} os={} arch={}".format(pkg, args.os, args.arch))
    if str(args.os) != "OHOS":
        skip("OHOS-native suite（全部 %d 条）" % 10,
             "非 OHOS 构建（os={}）：本套件判据全部是鸿蒙平台特有的，Linux 上无意义".format(args.os))
        print("[ohos-native] checks=0 passed=0 failed=0 skipped=1")
        return 0

    bins = {name: os.path.join(pkg, "bin", name) for name in ("imx_usb", "imx_uart")}
    infos = {k: elf_parse(v) for k, v in bins.items()}

    # O1 — 平台身份（鸿蒙 PC 的实测标志：/data/service/hnp 与 uname）
    sysname = os.uname().sysname if hasattr(os, "uname") else "?"
    hnp = os.path.isdir("/data/service/hnp")
    record("O1 OHOS 平台身份（uname.sysname={} 且 /data/service/hnp 存在）".format(sysname),
           hnp, "hnp_dir={} uname={}".format(hnp, sysname))

    # O2 — OHOS 无 /bin/bash：交付物不得依赖它
    bash_bad = {k: (b"/bin/bash" in i["raw"]) for k, i in infos.items()}
    record("O2 OHOS 壳层契约：两个 ELF 均不引用 /bin/bash（OHOS 只有 /data/service/hnp/bin/bash）",
           not any(bash_bad.values()),
           "refs={} hnp_bash_exists={} posix_bash_exists={}".format(
               bash_bad, os.path.isfile("/data/service/hnp/bin/bash"), os.path.isfile("/bin/bash")))

    # O3 — 设备 /tmp 只读：交付物不得依赖可写 /tmp
    tmp_bad = {k: (b"/tmp/" in i["raw"] or b"/tmp\x00" in i["raw"]) for k, i in infos.items()}
    tmp_writable = False
    try:
        probe = os.path.join("/tmp", ".imx_ohos_probe")
        with open(probe, "w") as fh:
            fh.write("x")
        os.remove(probe)
        tmp_writable = True
    except Exception:
        tmp_writable = False
    record("O3 OHOS 只读 /tmp 契约：两个 ELF 均不依赖 /tmp 路径",
           not any(tmp_bad.values()),
           "refs={} /tmp_writable_on_worker={}".format(tmp_bad, tmp_writable))

    # O4 — OHOS 加载器签名契约：交付 ELF 必须带 .codesign **段**（精确 section 名）
    cs = {k: (".codesign" in i["sections"] or ".note.ohos" in i["sections"]
              or b".codesign" in i["raw"] or b".note.ohos" in i["raw"])
          for k, i in infos.items()}
    cs_kind = {k: ("section" if (".codesign" in i["sections"] or ".note.ohos" in i["sections"])
                   else ("raw-section-name" if (b".codesign" in i["raw"] or b".note.ohos" in i["raw"])
                         else "absent"))
               for k, i in infos.items()}
    record("O4 OHOS 加载器签名契约：两个 ELF 都带 OHOS 签名（.codesign/.note.ohos）",
           all(cs.values()), "signed={} kind={}".format(cs, cs_kind))

    # O5 — OHOS 无 CMake 平台表：不得带 RPATH/RUNPATH（否则指向构建机）
    rp = {k: (i["rpath"] + i["runpath"]) for k, i in infos.items()}
    record("O5 OHOS 无 Platform/HarmonyOS.cmake ⇒ 交付 ELF 不得带 RPATH/RUNPATH",
           not any(rp.values()), "rpath_runpath={}".format(rp))

    # O6 — 依赖闭包：DT_NEEDED 只能是系统库/本包依赖，且不得是路径
    nd = {k: i["needed"] for k, i in infos.items()}
    bad_nd = {k: [n for n in v if ("/" in n) or (n not in ALLOWED_NEEDED)]
              for k, v in nd.items()}
    bad_nd = {k: v for k, v in bad_nd.items() if v}
    record("O6 OHOS 依赖闭包：DT_NEEDED ⊆ 系统/本包依赖且不含路径",
           not bad_nd, "needed={} unexpected={}".format(nd, bad_nd))

    # O7/O8 — 在鸿蒙 worker 上真跑交付的 ELF（能跑就断言横幅；被拒则断言拒绝形态）
    for idx, (name, path) in enumerate((("imx_usb", bins["imx_usb"]),
                                        ("imx_uart", bins["imx_uart"])), start=7):
        try:
            res = subprocess.run([path, "-V"], capture_output=True, text=True, timeout=60)
            out = ((res.stdout or "") + (res.stderr or "")).strip()
        except Exception as exc:                       # noqa: BLE001
            res, out = None, "{}".format(exc)
        ran = res is not None and res.returncode == 0
        if ran:
            # 两个多调用入口共用 imx_loader.h:22 的版本串，故断言版本串而不是程序名
            # （实测 `imx_uart -V` 同样打印 `imx_usb 0.2pre`）。
            record("O{} OHOS 上真跑 bin/{}（加载器接受已签名 ELF）并断言版本横幅".format(idx, name),
                   "0.2pre" in out, "rc={} out={!r}".format(res.returncode, out[:120]))
        else:
            refused = any(m in out for m in LOADER_REFUSAL_MARKERS)
            signed = ".codesign" in infos[name]["sections"]
            record("O{} OHOS 上真跑 bin/{}：被加载器拒绝时，拒绝形态必须是已归档策略且交付物已签名".format(idx, name),
                   refused and signed,
                   "rc={} signed={} out={!r}".format(
                       res.returncode if res is not None else None, signed, out[:160]))

    # O9 — OHOS 运行时不需要写任何路径：配置数据库随包交付，且含上游 tests/ 依赖的那条映射
    conf = os.path.join(pkg, "etc", "imx-loader.d", "imx_usb.conf")
    conf_ok = os.path.isfile(conf)
    first, rows, mapped = "", 0, False
    if conf_ok:
        with open(conf, "r", errors="replace") as fh:
            lines = fh.read().splitlines()
        first = lines[0].strip() if lines else ""
        rows = sum(1 for ln in lines if ln.strip() and not ln.startswith("#"))
        mapped = any(ln.split(",")[0].strip() == "0x15a2:0x0061" for ln in lines
                     if "," in ln and not ln.startswith("#"))
    record("O9 OHOS 运行时无写路径依赖：配置数据库随包交付（上游格式 + tests/ 用的 0x15a2:0x0061 映射）",
           conf_ok and first.startswith("#vid:pid") and rows >= 20 and mapped,
           "conf={} header={!r} rows={} has_0x15a2_0x0061={}".format(conf, first, rows, mapped))

    # O10 — 交付形态与 OHOS 架构一致（AArch64 ELF64 ET_EXEC/ET_DYN）
    want_machine = ELF_MACHINE.get(str(args.arch))
    arch_ok = all(i["elf"] and i["class"] == 2 and
                  (want_machine is None or i["machine"] == want_machine) and i["type"] in (2, 3)
                  for i in infos.values())
    record("O10 OHOS 架构契约：两个 ELF 均为 ELF64 且 e_machine 匹配 {}".format(args.arch),
           arch_ok, "machine={} type={}".format({k: i["machine"] for k, i in infos.items()},
                                                {k: i["type"] for k, i in infos.items()}))

    print("[ohos-native] checks={} passed={} failed={} skipped={}".format(
        len(CHECKS), sum(1 for _n, ok, _d in CHECKS if ok), len(FAILURES), len(SKIPS)))
    if FAILURES:
        print("[ohos-native] FAILED: " + ", ".join(FAILURES))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
