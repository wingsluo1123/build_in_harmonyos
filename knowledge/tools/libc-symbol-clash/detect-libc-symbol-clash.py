#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""detect-libc-symbol-clash.py — musl/UAPI 符号冲突检测器（知识库拓展 B 类交付物）

类问题（glibc → OpenHarmony/musl 迁移）
--------------------------------------
glibc 生态里 UAPI 头（<linux/*.h>、<asm/*.h>）与 libc 头（<sys/*.h>、<netinet/*.h> …）
用 `#ifndef __GLIBC__` / `__KERNEL__` 守卫互斥，同名类型（如 struct sockaddr_storage）
不会同时可见。OpenHarmony 的 musl 派生 sysroot 带了 bionic 派生的 UAPI 头，缺这层互斥：
同一编译单元只要既引入 libc 头、又引入 netlink/UAPI 头，就报

    error: redefinition of 'struct sockaddr_storage'

在 glibc 上完全正常。正确修法是 **libc 鉴别探针**（`#if defined(__linux__) &&
!defined(__GLIBC__)`）并在引入 UAPI 头期间重命名内核侧定义，而不是 `__OHOS__` 平台宏
（不可移植；补丁里写平台宏会被 preflight PF5 拦下）。

四种模式
--------
  sysroot   --sysroot DIR            在给定 sysroot 上实测 libc 侧 × UAPI 侧重名声明（权威）
  source    --src DIR [--sysroot DIR] 项目源码声明 vs libc/UAPI 符号集合（重定义风险）
  includes  --src DIR [--sysroot DIR] TU 级：同一编译单元是否同时引入冲突头文件对（kea 案例，
                                      无 sysroot 也可用内置基线触发）
  lint      --patches DIR            补丁新增行里的不可移植平台宏（__OHOS__），并给出推荐 guard

设计约束（知识库拓展要求）
--------------------------
* 仅标准库；无网络；不依赖本地缓存；不写死绝对路径（sysroot/src 均由参数或环境给出）
* 可在 OHOS aarch64 的 python3 直接运行；输出确定性；退出码对脚本友好
* 无 sysroot 时退化为内置基线表（每条带 evidence/confidence 字段，未实证项显式标 candidate）

退出码
------
  0  无 HIGH/MEDIUM 命中
  1  存在 HIGH/MEDIUM 命中
  2  用法/参数错误
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

TOOL_VERSION = "1.0.0"

SEV_ORDER = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}

# ───────────────────────────── 内置冲突基线 ─────────────────────────────
# confidence:
#   verified  — 真实适配案例中确认（附归档证据）
#   candidate — 同族已知的 libc × UAPI 定义重叠，需 --sysroot 实测复核
#
# libc_triggers / uapi_triggers 为“引入即意味着该侧定义可见”的头文件集合：
# 例如 musl 的 <net/if.h>、<netinet/in.h> 都会拉入 <sys/socket.h> 的定义，
# 因此 TU 里出现 net/if.h + linux/rtnetlink.h 即构成潜在冲突（kea 实测案例）。
BASELINE = [
    {
        "id": "CLASH-001",
        "ident": "sockaddr_storage",
        "libc_header": "sys/socket.h",
        "uapi_header": "linux/socket.h",
        "libc_triggers": ["sys/socket.h", "net/if.h", "netinet/in.h", "arpa/inet.h",
                          "netdb.h", "netpacket/packet.h", "sys/un.h"],
        "uapi_triggers": ["linux/socket.h", "linux/rtnetlink.h", "linux/netlink.h",
                          "linux/if_link.h", "linux/if_addr.h", "linux/neighbour.h"],
        "severity": "HIGH",
        "confidence": "verified",
        "evidence": "kea 3.0.3 实测：src/lib/dhcp/iface_mgr_linux.cc 经 <net/if.h> 取得 libc 侧 "
                    "struct sockaddr_storage，又引入 <linux/rtnetlink.h>，musl 派生 sysroot 报重定义；"
                    "归档补丁 patches/0002-src-lib-dhcp-iface_mgr_linux.cc.patch 以 libc 鉴别探针重命名"
                    "内核侧定义修复（archives/k/kea-hook-host-cmds/3.0.3）",
    },
    {
        "id": "CLASH-002",
        "ident": "sockaddr",
        "libc_header": "sys/socket.h",
        "uapi_header": "linux/socket.h",
        "libc_triggers": ["sys/socket.h", "net/if.h", "netinet/in.h", "arpa/inet.h", "sys/un.h"],
        "uapi_triggers": ["linux/socket.h", "linux/rtnetlink.h", "linux/netlink.h"],
        "severity": "MEDIUM",
        "confidence": "candidate",
        "evidence": "musl <sys/socket.h> 与 bionic 派生 <linux/socket.h> 的内核侧定义同名；需 --sysroot 复核",
    },
    {
        "id": "CLASH-003",
        "ident": "msghdr",
        "libc_header": "sys/socket.h",
        "uapi_header": "linux/socket.h",
        "libc_triggers": ["sys/socket.h", "net/if.h", "netinet/in.h"],
        "uapi_triggers": ["linux/socket.h", "linux/rtnetlink.h", "linux/netlink.h"],
        "severity": "MEDIUM",
        "confidence": "candidate",
        "evidence": "musl <sys/socket.h> struct msghdr 与 bionic 派生内核侧定义同名；需 --sysroot 复核",
    },
    {
        "id": "CLASH-004",
        "ident": "iovec",
        "libc_header": "sys/uio.h",
        "uapi_header": "linux/uio.h",
        "libc_triggers": ["sys/uio.h", "sys/stat.h"],
        "uapi_triggers": ["linux/uio.h", "linux/fs.h"],
        "severity": "MEDIUM",
        "confidence": "candidate",
        "evidence": "musl <sys/uio.h> struct iovec 与 bionic 派生 <linux/uio.h> 同名；需 --sysroot 复核",
    },
    {
        "id": "CLASH-005",
        "ident": "in_addr",
        "libc_header": "netinet/in.h",
        "uapi_header": "linux/in.h",
        "libc_triggers": ["netinet/in.h", "arpa/inet.h", "netdb.h"],
        "uapi_triggers": ["linux/in.h", "linux/in6.h"],
        "severity": "MEDIUM",
        "confidence": "candidate",
        "evidence": "musl <netinet/in.h> struct in_addr 与 bionic 派生 <linux/in.h> 同名；需 --sysroot 复核",
    },
    {
        "id": "CLASH-006",
        "ident": "ifreq",
        "libc_header": "net/if.h",
        "uapi_header": "linux/if.h",
        "libc_triggers": ["net/if.h"],
        "uapi_triggers": ["linux/if.h", "linux/if_link.h", "linux/if_addr.h", "linux/rtnetlink.h"],
        "severity": "MEDIUM",
        "confidence": "candidate",
        "evidence": "<net/if.h> 与 <linux/if.h> 的 struct ifreq/ifmap 历来不可共存（多平台已知）；需 --sysroot 复核",
    },
    {
        "id": "CLASH-007",
        "ident": "termios",
        "libc_header": "termios.h",
        "uapi_header": "asm/termbits.h",
        "libc_triggers": ["termios.h", "sys/ioctl.h", "unistd.h"],
        "uapi_triggers": ["asm/termbits.h", "asm/termios.h", "linux/tty.h"],
        "severity": "MEDIUM",
        "confidence": "candidate",
        "evidence": "libc struct termios 与内核侧 termios/termios2 定义重叠；需 --sysroot 复核",
    },
    {
        "id": "CLASH-008",
        "ident": "stat",
        "libc_header": "sys/stat.h",
        "uapi_header": "asm/stat.h",
        "libc_triggers": ["sys/stat.h"],
        "uapi_triggers": ["asm/stat.h", "linux/stat.h"],
        "severity": "MEDIUM",
        "confidence": "candidate",
        "evidence": "musl <sys/stat.h> 与内核侧 struct stat 定义重叠（内核侧通常带 __KERNEL__ 守卫）；需 --sysroot 复核",
    },
]

# 头文件家族分类（用于 --sysroot 实测与 includes 归属）
UAPI_PREFIXES = ("linux/", "asm/", "asm-generic/", "mtd/", "sound/", "drm/", "xen/",
                 "video/", "scsi/", "rdma/", "misc/")
LIBC_PREFIXES = ("sys/", "netinet/", "arpa/", "net/", "bits/", "netpacket/", "rpc/",
                 "protocols/", "scsi/")
LIBC_BARE = {
    "assert.h", "complex.h", "ctype.h", "dirent.h", "dlfcn.h", "errno.h", "fcntl.h",
    "fenv.h", "float.h", "glob.h", "grp.h", "iconv.h", "inttypes.h", "langinfo.h",
    "libgen.h", "limits.h", "locale.h", "math.h", "monetary.h", "mqueue.h", "nl_types.h",
    "paths.h", "poll.h", "pthread.h", "pwd.h", "regex.h", "sched.h", "search.h",
    "semaphore.h", "setjmp.h", "signal.h", "spawn.h", "stdarg.h", "stdbool.h", "stddef.h",
    "stdint.h", "stdio.h", "stdlib.h", "string.h", "strings.h", "stropts.h", "syslog.h",
    "tar.h", "termios.h", "tgmath.h", "time.h", "trace.h", "ucontext.h", "ulimit.h",
    "unistd.h", "utime.h", "utmp.h", "utmpx.h", "wchar.h", "wctype.h", "wordexp.h",
}

GUARD_TEMPLATE = """\
/* 在引入 UAPI 头期间重命名内核侧定义（libc 鉴别探针，非平台宏；R8 口径） */
#if defined(__linux__) && !defined(__GLIBC__)
#  define %(ident)s __linux_uapi_%(ident)s
#  define %(prefix)s_RESTORE_%(ident)s 1
#endif
#include <%(uapi_header)s>
#ifdef %(prefix)s_RESTORE_%(ident)s
#  undef %(ident)s
#  undef %(prefix)s_RESTORE_%(ident)s
#endif

/* 若冲突来自“先 UAPI 后 libc”的顺序，把同样的探针包在 libc 头之前，或改在 TU 末尾
 * 单独引入 UAPI 头；不要用 `#ifdef __OHOS__`（不可移植，preflight PF5 会拦）。
 * 参考实证：archives/k/kea-hook-host-cmds/3.0.3/patches/0002-*.patch
 */"""

TEMPLATE_PLACEHOLDER = "PKGNAME"

INCLUDE_RE = re.compile(r'^\s*#\s*include\s*[<"]([^>"]+)[>"]')
TYPE_TAG_RE = re.compile(r'\b(?:struct|union|enum|class)\s+([A-Za-z_]\w*)\s*(?=\{|;|:|\n|\))')
TYPEDEF_RE = re.compile(r'\btypedef\b[^;{}]*?([A-Za-z_]\w*)\s*;')
DEFINE_RE = re.compile(r'^\s*#\s*define\s+([A-Za-z_]\w*)')

SRC_SUFFIXES = (".c", ".cc", ".cpp", ".cxx", ".c++")
HDR_SUFFIXES = (".h", ".hh", ".hpp", ".hxx", ".inc")

SKIP_DIRS = {".git", ".svn", "build", "_build", "CMakeFiles", ".cache", "node_modules"}


# ───────────────────────────── 基础工具 ─────────────────────────────

def iter_files(root: Path, suffixes):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn.endswith(suffixes):
                yield Path(dirpath) / fn


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _normalize_header(name: str) -> str:
    """把头文件路径归一化为 'sys/socket.h' 形态：sysroot 内为 <root>/usr/include/x.h。"""
    n = name.replace("\\", "/").lstrip("./")
    for marker in ("/usr/include/", "usr/include/", "/include/", "include/"):
        idx = n.find(marker)
        if idx >= 0:
            return n[idx + len(marker):]
    return n


def classify_header(name: str) -> str:
    """libc | uapi | other —— 依头文件路径家族判定（兼容 'sys/x.h' 与 '<root>/usr/include/sys/x.h'）。"""
    n = _normalize_header(name)
    if n.startswith(UAPI_PREFIXES):
        return "uapi"
    base = n.rsplit("/", 1)[-1]
    if base in LIBC_BARE:
        return "libc"
    if n.startswith(LIBC_PREFIXES):
        return "libc"
    return "other"


GUARD_PROBE_RE = re.compile(r'__GLIBC__|__BIONIC__|__UCLIBC__|__musl__')


def guard_witness(text: str, ident: str):
    """TU 内已有针对 ident 的 guard 见证 → (行号, 行内容)，否则 None。

    只认强见证：`#define <ident> <新名>`（引入 UAPI 头期间改名）或 `#undef <ident>`（还原）。
    仅仅出现 libc 鉴别探针（__GLIBC__ 等）不足以证明该符号已被处理，故不降级，只记提示。
    """
    define_re = re.compile(r'^\s*#\s*define\s+' + re.escape(ident) + r'\s+\S')
    undef_re = re.compile(r'^\s*#\s*undef\s+' + re.escape(ident) + r'\b')
    for i, line in enumerate(text.splitlines(), 1):
        if define_re.match(line) or undef_re.match(line):
            return (i, line.strip()[:160])
    return None


def scan_declarations(text: str):
    """粗粒度声明抽取：type tag / typedef / #define -> {name: [(kind, lineno)]}。"""
    out: dict[str, list[tuple[str, int]]] = {}
    for i, line in enumerate(text.splitlines(), 1):
        code = line.split("/*", 1)[0]
        if code.lstrip().startswith("//"):
            continue
        m = DEFINE_RE.match(code)
        if m:
            out.setdefault(m.group(1), []).append(("macro", i))
        for m in TYPE_TAG_RE.finditer(code):
            out.setdefault(m.group(1), []).append(("type", i))
        for m in TYPEDEF_RE.finditer(code):
            out.setdefault(m.group(1), []).append(("typedef", i))
    return out


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def json_out(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


# ───────────────────────────── 报告渲染 ─────────────────────────────

def render_finding(f, verbose=True):
    lines = []
    conf = f.get("confidence", "candidate")
    tag = "verified" if conf == "verified" else "candidate(需 sysroot 复核)"
    lines.append(f"[{f['severity']}] {f['id']}  {f['ident']}  ({tag})")
    lines.append(f"  冲突对: libc <{f['libc_header']}>  ×  UAPI <{f['uapi_header']}>")
    if f.get("where"):
        lines.append(f"  位置: {f['where']}")
    for ev in f.get("evidence_lines", []):
        lines.append(f"    证据: {ev}")
    if f.get("detail"):
        lines.append(f"  说明: {f['detail']}")
    if verbose:
        body = GUARD_TEMPLATE % {"ident": f["ident"], "uapi_header": f["uapi_header"],
                                 "prefix": TEMPLATE_PLACEHOLDER}
        lines.append("  修法（推荐 guard 模板）:")
        for ln in body.splitlines():
            lines.append("    " + ln)
    return "\n".join(lines)


def summarize(findings):
    by_sev = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for f in findings:
        by_sev[f["severity"]] = by_sev.get(f["severity"], 0) + 1
    return by_sev


def emit(findings, args, mode, target, scanned=0, extra=None):
    findings = [f for f in findings
                if SEV_ORDER.get(f["severity"], 0) >= SEV_ORDER[args.min_severity]
                and f["id"] not in args.ignore_ids]
    findings.sort(key=lambda f: (-SEV_ORDER.get(f["severity"], 0), f["id"], f.get("where", "")))
    by_sev = summarize(findings)
    payload = {
        "tool": "detect-libc-symbol-clash",
        "version": TOOL_VERSION,
        "mode": mode,
        "target": str(target),
        "sysroot": str(args.sysroot) if args.sysroot else None,
        "baseline_entries": len(BASELINE),
        "scanned": scanned,
        "summary": {"HIGH": by_sev["HIGH"], "MEDIUM": by_sev["MEDIUM"], "LOW": by_sev["LOW"],
                    "total": len(findings)},
        "findings": findings,
    }
    if extra:
        payload.update(extra)

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.json:
        json_out(payload)
    else:
        print(f"musl/UAPI 符号冲突检测  mode={mode}  target={target}")
        print(f"  sysroot: {args.sysroot if args.sysroot else '（未提供，使用内置基线 %d 条）' % len(BASELINE)}")
        print(f"  扫描: {scanned}  命中: {len(findings)} "
              f"(HIGH {by_sev['HIGH']} / MEDIUM {by_sev['MEDIUM']} / LOW {by_sev['LOW']})")
        for f in findings:
            print()
            print(render_finding(f, verbose=not args.no_template))
        if not findings:
            print("\n未发现命中（阈值 %s）" % args.min_severity)
    if args.out:
        print(f"\n报告已写入: {args.out}", file=sys.stderr)
    return 1 if (by_sev["HIGH"] or by_sev["MEDIUM"]) else 0


# ───────────────────────────── 模式 1: sysroot ─────────────────────────────

def mode_sysroot(args):
    """在真实 sysroot 上实测：同一标识符在 libc 侧与 UAPI 侧都有声明。"""
    root = Path(args.sysroot)
    if not root.is_dir():
        print(f"错误: sysroot 不存在: {root}", file=sys.stderr)
        return 2
    libc_idx: dict[str, list[tuple[str, int]]] = {}
    uapi_idx: dict[str, list[tuple[str, int]]] = {}
    n = 0
    for h in iter_files(root, HDR_SUFFIXES):
        fam = classify_header(rel(h, root))
        if fam not in ("libc", "uapi"):
            continue
        n += 1
        idx = libc_idx if fam == "libc" else uapi_idx
        for name, decls in scan_declarations(read_text(h)).items():
            idx.setdefault(name, []).extend((rel(h, root), ln) for _, ln in decls)

    known = {e["ident"]: e for e in BASELINE}
    findings = []
    for name in sorted(set(libc_idx) & set(uapi_idx)):
        libc_spots = libc_idx[name][:2]
        uapi_spots = uapi_idx[name][:2]
        entry = known.get(name)
        severity = entry["severity"] if entry else "MEDIUM"
        findings.append({
            "id": entry["id"] if entry else "CLASH-EXTRACTED",
            "ident": name,
            "libc_header": libc_spots[0][0],
            "uapi_header": uapi_spots[0][0],
            "severity": severity,
            "confidence": entry["confidence"] if entry else "verified",
            "where": f"sysroot={root}",
            "evidence_lines": [f"libc  <{h}>:{ln}" for h, ln in libc_spots]
                               + [f"UAPI <{h}>:{ln}" for h, ln in uapi_spots],
            "detail": entry["evidence"] if entry else "sysroot 实测：两侧同名声明（首次实测发现，建议补入基线表）",
        })
    return emit(findings, args, "sysroot", root, scanned=n,
                extra={"libc_symbols": len(libc_idx), "uapi_symbols": len(uapi_idx)})


# ───────────────────────────── 模式 2: source ─────────────────────────────

def mode_source(args):
    """项目源码声明 vs libc/UAPI 符号集合（重定义风险）。"""
    src = Path(args.src)
    if not src.is_dir():
        print(f"错误: src 不存在: {src}", file=sys.stderr)
        return 2

    libc_syms: dict[str, str] = {}
    uapi_syms: dict[str, str] = {}
    if args.sysroot:
        root = Path(args.sysroot)
        if not root.is_dir():
            print(f"错误: sysroot 不存在: {root}", file=sys.stderr)
            return 2
        for h in iter_files(root, HDR_SUFFIXES):
            fam = classify_header(rel(h, root))
            if fam not in ("libc", "uapi"):
                continue
            for name in scan_declarations(read_text(h)):
                (libc_syms if fam == "libc" else uapi_syms)[name] = rel(h, root)
    else:
        for e in BASELINE:
            libc_syms[e["ident"]] = e["libc_header"]
            uapi_syms[e["ident"]] = e["uapi_header"]

    known = {e["ident"]: e for e in BASELINE}
    findings, n = [], 0
    for p in iter_files(src, SRC_SUFFIXES + HDR_SUFFIXES):
        n += 1
        for name, decls in scan_declarations(read_text(p)).items():
            if name not in libc_syms and name not in uapi_syms:
                continue
            side = "libc" if name in libc_syms else "UAPI"
            other = uapi_syms if side == "libc" else libc_syms
            header = libc_syms.get(name) or uapi_syms[name]
            findings.append({
                "id": known[name]["id"] if name in known else "CLASH-SOURCE",
                "ident": name,
                "libc_header": header,
                "uapi_header": other.get(name, "-"),
                "severity": known[name]["severity"] if name in known else "MEDIUM",
                "confidence": known[name]["confidence"] if name in known else "candidate",
                "where": f"{p}:{decls[0][1]}",
                "evidence_lines": [f"项目侧声明 ({decls[0][0]}) 与 {side} 头 <{header}> 同名"],
                "detail": "项目自身定义了 libc/UAPI 已有名字，包含对应头文件即重定义；"
                          "改名或加 libc 鉴别探针隔离（勿用平台宏）",
            })
    return emit(findings, args, "source", src, scanned=n,
                extra={"libc_symbols": len(libc_syms), "uapi_symbols": len(uapi_syms)})


# ───────────────────────────── 模式 3: includes ─────────────────────────────

def build_project_index(src: Path):
    rel_index: dict[str, Path] = {}
    base_index: dict[str, list[Path]] = {}
    for h in iter_files(src, HDR_SUFFIXES):
        r = str(h.relative_to(src)).replace("\\", "/")
        rel_index.setdefault(r, h)
        base_index.setdefault(r.rsplit("/", 1)[-1], []).append(h)
    return rel_index, base_index


def resolve_include(name, cur_file: Path, src: Path, rel_index, base_index):
    cand = cur_file.parent / name
    if cand.is_file():
        return cand
    n = name.replace("\\", "/").lstrip("./")
    if n in rel_index:
        return rel_index[n]
    hits = base_index.get(n.rsplit("/", 1)[-1], [])
    for h in hits:
        # 优先匹配以 name 结尾的路径（kea 的 <dhcp/xxx.h> 风格，-I src/lib）
        if str(h.relative_to(src)).replace("\\", "/").endswith("/" + n) or \
           str(h.relative_to(src)).replace("\\", "/") == n:
            return h
    return hits[0] if hits else None


def collect_includes(src: Path, tu: Path, rel_index, base_index, max_depth=10):
    """返回 (system_headers: {name: [(file, line)]}, project_files: [rel...])，递归解析项目内头。"""
    system: dict[str, list[tuple[str, int]]] = {}
    seen, stack = set(), [(tu, 0)]
    while stack:
        f, depth = stack.pop()
        if f in seen or depth > max_depth:
            continue
        seen.add(f)
        for i, line in enumerate(read_text(f).splitlines(), 1):
            m = INCLUDE_RE.match(line)
            if not m:
                continue
            inc = m.group(1)
            fam = classify_header(inc)
            resolved = resolve_include(inc, f, src, rel_index, base_index)
            if resolved is not None and classify_header(inc) == "other":
                stack.append((resolved, depth + 1))
                continue
            if fam in ("libc", "uapi"):
                system.setdefault(inc, []).append((rel(f, src), i))
    return system, sorted(rel(p, src) for p in seen)


def mode_includes(args):
    src = Path(args.src)
    if not src.is_dir():
        print(f"错误: src 不存在: {src}", file=sys.stderr)
        return 2
    rel_index, base_index = build_project_index(src)

    rules = [dict(e) for e in BASELINE]
    extra = {}
    measured = None
    if args.sysroot:
        # sysroot 实测：只有两侧都声明的标识符才算真实冲突（权威口径，用于剔除未复现候选）
        root = Path(args.sysroot)
        if not root.is_dir():
            print(f"错误: sysroot 不存在: {root}", file=sys.stderr)
            return 2
        libc_names, uapi_names = set(), set()
        for h in iter_files(root, HDR_SUFFIXES):
            fam = classify_header(rel(h, root))
            if fam not in ("libc", "uapi"):
                continue
            for name in scan_declarations(read_text(h)):
                (libc_names if fam == "libc" else uapi_names).add(name)
        measured = libc_names & uapi_names
        extra = {"sysroot_measured_clashes": sorted(measured)[:40],
                 "sysroot_measured_count": len(measured)}

    findings, n_tu = [], 0
    for tu in iter_files(src, SRC_SUFFIXES):
        n_tu += 1
        system, _ = collect_includes(src, tu, rel_index, base_index)
        if not system:
            continue
        tu_text = read_text(tu)
        for e in rules:
            libc_hits = [h for h in e["libc_triggers"] if h in system]
            uapi_hits = [h for h in e["uapi_triggers"] if h in system]
            if not (libc_hits and uapi_hits):
                continue
            if measured is not None and e["ident"] not in measured:
                continue  # sysroot 实测未复现 → 该环境无需 guard，剔除候选
            ev = []
            for h in libc_hits[:2]:
                f, ln = system[h][0]
                ev.append(f"{f}:{ln} -> <{h}>（libc 侧定义）")
            for h in uapi_hits[:2]:
                f, ln = system[h][0]
                ev.append(f"{f}:{ln} -> <{h}>（UAPI 侧定义）")
            severity, confidence, detail = e["severity"], e["confidence"], e["evidence"]
            if measured is not None:
                confidence = "verified"  # 经真实 sysroot 复核
            witness = guard_witness(tu_text, e["ident"])
            if witness:
                severity, confidence = "LOW", "guarded"
                ev.append(f"{rel(tu, src)}:{witness[0]} -> 已 guard: {witness[1]}")
                detail = f"{detail}；该 TU 已有 guard 见证（改名/还原），降级为 LOW 留痕"
            elif GUARD_PROBE_RE.search(tu_text):
                detail = f"{detail}；TU 内存在 libc 鉴别探针，请确认是否已覆盖该符号"
            findings.append({
                "id": e["id"],
                "ident": e["ident"],
                "libc_header": e["libc_header"],
                "uapi_header": e["uapi_header"],
                "severity": severity,
                "confidence": confidence,
                "where": rel(tu, src),
                "evidence_lines": ev,
                "detail": detail,
            })
    return emit(findings, args, "includes", src, scanned=n_tu, extra=extra)


# ───────────────────────────── 模式 4: lint ─────────────────────────────

def lint_text(text: str, label: str):
    findings = []
    for i, line in enumerate(text.splitlines(), 1):
        if not line.startswith("+"):
            continue
        if line.startswith("+++") or line.startswith("+--- ") or line.startswith("+index "):
            continue
        body = line[1:]
        if "__OHOS__" in body:
            findings.append({
                "id": "GUARD-001", "ident": "platform-macro __OHOS__",
                "libc_header": "-", "uapi_header": "-",
                "severity": "HIGH", "confidence": "verified",
                "where": f"{label}:{i}",
                "evidence_lines": [body.strip()[:160]],
                "detail": "补丁新增行使用平台宏 __OHOS__：不可移植且会被 preflight PF5 拦下；"
                          "改用 libc 鉴别探针（__linux__ && !__GLIBC__）隔离 musl 与 glibc 差异",
            })
    return findings


def mode_lint(args):
    target = Path(args.patches)
    if not target.is_dir():
        print(f"错误: patches 目录不存在: {target}", file=sys.stderr)
        return 2
    findings, n = [], 0
    for p in sorted(target.rglob("*")):
        if not p.is_file() or p.suffix not in (".patch", ".diff"):
            continue
        n += 1
        findings.extend(lint_text(read_text(p), rel(p, target)))
    return emit(findings, args, "lint", target, scanned=n)


# ───────────────────────────── CLI ─────────────────────────────

def autodetect_sysroot():
    """从环境推断 sysroot（全部为可选提示，不写死任何绝对路径）。"""
    for var in ("OHOS_SYSROOT", "OHC_SYSROOT"):
        v = os.environ.get(var)
        if v and Path(v).is_dir():
            return v
    for var in ("OHOS_SDK", "OHOS_SDK_ROOT", "OHOS_SDK_NATIVE", "OHC_OHOS_SDK"):
        v = os.environ.get(var)
        if not v:
            continue
        for cand in (Path(v) / "sysroot", Path(v) / "usr", Path(v)):
            if cand.is_dir():
                return str(cand)
    for var in ("CPPFLAGS", "CFLAGS", "CXXFLAGS"):
        for m in re.finditer(r"--sysroot[= ](\S+)", os.environ.get(var, "")):
            if Path(m.group(1)).is_dir():
                return m.group(1)
    return None


def print_template(ident="sockaddr_storage", uapi_header="linux/socket.h", pkg="PKGNAME"):
    print(GUARD_TEMPLATE % {"ident": ident, "uapi_header": uapi_header, "prefix": pkg})


def build_parser():
    ap = argparse.ArgumentParser(
        prog="detect-libc-symbol-clash.py",
        description="musl/UAPI 符号冲突检测器（libc × 内核 UAPI 同名定义 → 重定义/编译失败）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n"
               "  %(prog)s includes --src src/            # kea 类冲突（无需 sysroot）\n"
               "  %(prog)s includes --src src/ --sysroot $OHOS_SYSROOT\n"
               "  %(prog)s sysroot --sysroot $OHOS_SYSROOT --out report.json\n"
               "  %(prog)s lint --patches patches/\n"
               "  %(prog)s --print-template\n")
    ap.add_argument("mode", nargs="?", choices=["sysroot", "source", "includes", "lint"])
    ap.add_argument("--sysroot", default=None, help="sysroot 目录（缺省时尝试环境推断，再退化为内置基线）")
    ap.add_argument("--src", default=None, help="项目源码目录（source/includes 模式）")
    ap.add_argument("--patches", default=None, help="补丁目录（lint 模式）")
    ap.add_argument("--json", action="store_true", help="JSON 输出（机器可读）")
    ap.add_argument("--out", default=None, help="报告落盘路径（JSON）")
    ap.add_argument("--min-severity", default="MEDIUM", choices=["HIGH", "MEDIUM", "LOW"])
    ap.add_argument("--ignore", default="", help="忽略的规则 ID（逗号分隔，如 CLASH-006,CLASH-007）")
    ap.add_argument("--no-template", action="store_true", help="报告不附 guard 模板（精简输出）")
    ap.add_argument("--no-baseline", action="store_true", help="不加载内置基线（仅用 sysroot 实测结果）")
    ap.add_argument("--print-template", action="store_true", help="打印 guard 模板并退出")
    ap.add_argument("--version", action="version", version=f"%(prog)s {TOOL_VERSION}")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.ignore_ids = {s.strip() for s in args.ignore.split(",") if s.strip()}

    if args.print_template:
        print_template()
        return 0
    if not args.mode:
        build_parser().print_help()
        return 2

    global BASELINE
    if args.no_baseline:
        BASELINE = []

    if args.mode in ("source", "includes") and not args.src:
        print(f"错误: mode={args.mode} 需要 --src DIR", file=sys.stderr)
        return 2
    if args.mode == "sysroot" and not args.sysroot:
        args.sysroot = autodetect_sysroot()
        if not args.sysroot:
            print("错误: mode=sysroot 需要 --sysroot DIR（环境推断失败）", file=sys.stderr)
            return 2
    if args.mode == "lint" and not args.patches:
        print("错误: mode=lint 需要 --patches DIR", file=sys.stderr)
        return 2
    if not args.sysroot and args.mode != "lint":
        args.sysroot = autodetect_sysroot()
        if args.sysroot:
            print(f"[i] 自动推断 sysroot: {args.sysroot}", file=sys.stderr)

    return {"sysroot": mode_sysroot, "source": mode_source,
            "includes": mode_includes, "lint": mode_lint}[args.mode](args)


if __name__ == "__main__":
    sys.exit(main())
