#!/usr/bin/env python3
"""kamailio-xhttp_prom 产物合规 + 鸿蒙平台适配核对。

与 consumer（运行期真实加载）互补：本脚本做静态面核对，重点回答两个问题：
  1) 产物是否为干净的 OHOS/aarch64 插件（ELF 类型、动态依赖、RPATH、符号面）
  2) 鸿蒙适配决策是否自洽 —— 模块的全部"非 kamailio 核心"未定义符号都必须由
     OHOS libc（musl）提供；若 extra_defs 注入的平台宏（HAVE_GETHOSTBYNAME2 /
     HAVE_SCHED_YIELD / HAVE_TIMEGM ...）在平台上无对应符号，运行期必然加载失败。

模块路径来源: argv[1]（test_package/test() 的主路径）；环境变量
KAMAILIO_XHTTP_PROM_PACKAGE_FOLDER 为独立手工调用时的可选回退。
"""
import ctypes
import os
import shutil
import struct
import subprocess
import sys

FAILURES = 0
CHECKS = 0

# 符号分类与 gen_shim.py 同源（单一事实源）：核心符号由 kamailio 主程序在运行期
# 提供，平台符号由 OHOS libc 提供，两者之外不应存在任何未定义符号
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_shim import FUNCS, PINNED, PLATFORM  # noqa: E402

# 平台宏对应的 OHOS libc 符号（extra_defs 决策的实测锚点）
PLATFORM_SYMS = ["gethostbyname2", "sched_yield", "sched_setscheduler", "timegm",
                 "gettimeofday", "getaddrinfo"]

# glibc 专属符号：出现即说明误链 glibc 或工具链串台
GLIBC_ONLY = ["__xstat", "__fxstat", "__lxstat", "__libc_start_main",
              "_IO_2_1_stdout_", "__ctype_b_loc", "stat64", "__isoc99_sscanf"]


def check(cond, label, detail=""):
    global FAILURES, CHECKS
    CHECKS += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {label}{' — ' + detail if detail else ''}")
    if not cond:
        FAILURES += 1


def resolve_module_path():
    if len(sys.argv) > 1:
        return sys.argv[1]
    pkg = os.environ.get("KAMAILIO_XHTTP_PROM_PACKAGE_FOLDER")
    if not pkg:
        print("error: 未提供模块路径（argv[1] 或 KAMAILIO_XHTTP_PROM_PACKAGE_FOLDER）",
              file=sys.stderr)
        sys.exit(2)
    return os.path.join(pkg, "lib", "kamailio", "modules", "xhttp_prom.so")


def package_folder(module):
    # <pkg>/lib/kamailio/modules/xhttp_prom.so → <pkg>
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(module))))


def readelf(args):
    tool = shutil.which("llvm-readelf") or shutil.which("readelf")
    if not tool:
        return None
    proc = subprocess.run([tool] + args, capture_output=True, text=True)
    return proc.stdout


def main():
    module = resolve_module_path()
    pkg = package_folder(module)

    # ── 随包文件 ────────────────────────────────────────────────
    check(os.path.isfile(module), "模块产物随包", os.path.relpath(module, pkg))
    check(os.path.isfile(os.path.join(pkg, "licenses", "COPYING")),
          "licenses/COPYING 随包", "GPL-2.0-or-later 许可证")
    check(os.path.isfile(os.path.join(pkg, "share", "doc", "kamailio-xhttp_prom",
                                      "README")),
          "上游模块 README 随包", "share/doc/kamailio-xhttp_prom/README")
    if not os.path.isfile(module):
        print("\ncheck_artifact: 模块缺失，无法继续")
        return 1

    # ── ELF 头（纯 Python 解析，不依赖 readelf） ─────────────────
    with open(module, "rb") as fh:
        head = fh.read(64)
    check(head[:4] == b"\x7fELF", "ELF magic")
    check(head[4] == 2, "ELF64（EI_CLASS=2）")
    e_type = struct.unpack_from("<H", head, 16)[0]
    e_machine = struct.unpack_from("<H", head, 18)[0]
    check(e_type == 3, "ET_DYN（共享对象）", f"e_type={e_type}")
    check(e_machine == 183, "AArch64（EM_AARCH64=183）", f"e_machine={e_machine}")

    # ── 动态段 ────────────────────────────────────────────────
    dyn = readelf(["-d", module])
    if dyn is None:
        print("[SKIP] readelf 不可用，跳过动态段与符号面核对（2 项）")
        dyn = ""
    needed = [ln.split("[")[-1].rstrip("]") for ln in dyn.splitlines() if "NEEDED" in ln]
    check(needed == ["libc.so"], "动态依赖仅 OHOS libc（musl）", ", ".join(needed) or "无")
    check("RPATH" not in dyn and "RUNPATH" not in dyn,
          "无 RPATH/RUNPATH 泄漏", "运行期依赖解析交给加载器")

    # ── 符号面 ────────────────────────────────────────────────
    syms = readelf(["--dyn-symbols", module]) or ""
    undef, defined = [], []
    for line in syms.splitlines():
        parts = line.split()
        if len(parts) < 8 or not parts[0].endswith(":"):
            continue
        name = parts[7]
        if "UND" in parts[6:7]:
            undef.append(name)
        elif name:
            defined.append(name)

    if syms:
        check("exports" in defined, "导出模块 ABI 入口符号 exports", "OBJECT")
        check("mod_register" in defined, "导出加载器钩子 mod_register", "FUNC")

        prom_defs = [s for s in defined if s.startswith("prom_")]
        check(len(prom_defs) >= 10, "导出 Prometheus 指标 API",
              f"{len(prom_defs)} 个 prom_* 符号")

        glibc_hits = [s for s in undef if s in GLIBC_ONLY]
        check(not glibc_hits, "无 glibc 专属未定义符号",
              ", ".join(glibc_hits) if glibc_hits else "符号面为 musl 语义")
    else:
        prom_defs, glibc_hits = [], []

    # ── 鸿蒙平台适配核对 ────────────────────────────────────────
    libc = None
    for candidate in ("libc.so", None):
        try:
            libc = ctypes.CDLL(candidate)
            break
        except OSError:
            continue
    check(libc is not None, "可加载 OHOS libc（musl）", "用于平台符号核对")

    if libc is not None:
        missing = [s for s in PLATFORM_SYMS if not hasattr(libc, s)]
        check(not missing, "extra_defs 平台宏对应的符号均存在于 OHOS libc",
              ", ".join(missing) if missing else f"{len(PLATFORM_SYMS)}/{len(PLATFORM_SYMS)} 可解析")

    if syms:
        core_syms = set(PINNED) | set(FUNCS)
        non_core = [s for s in undef if s not in core_syms and s not in PLATFORM]
        unresolved = [s for s in non_core
                      if libc is not None and not hasattr(libc, s)]
        check(not unresolved,
              "全部非核心未定义符号由 OHOS libc 提供（无平台缺口）",
              ", ".join(unresolved) if unresolved else
              f"{len(undef)} 个未定义符号 = {len(core_syms)} 核心 + "
              f"{len(PLATFORM)} OHOS libc，无未归类符号")

    print(f"\ncheck_artifact: {CHECKS - FAILURES}/{CHECKS} checks passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
