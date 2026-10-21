#!/usr/bin/env python3
"""detect_absent_service_crash.py — 检测「运行期服务缺失 → 清理路径崩溃」一类问题.

适用对象：宿主/客户端型程序（音频宿主、显示客户端、DBus 服务客户端……）在
目标平台上找不到它依赖的**运行期服务或设备**时，失败清理路径解引用了尚未
初始化的句柄，直接把「本应优雅退出」变成 SIGSEGV。

两个通道，可独立使用：

  L1 源码通道（scan）：在 cleanup/close/deactivate/free 类函数里找
     "循环中解引用惰性初始化句柄且无 NULL 守卫" 的形态，给出候选位置。

  L2 运行期通道（runtime）：解析运行日志或直接跑命令，要求
     「服务连接失败特征」与「崩溃特征」同时出现才判定为本类问题——
     只有连接失败 = 正常优雅失败，只有崩溃 = 另一类问题。

判定输出为稳定的机器可读行（便于 CI 断言）：

  ABSENT_SERVICE_CLEANUP_CANDIDATE=yes|no      # L1 结论
  ABSENT_SERVICE_CRASH_CONFIRMED=yes|no|unknown # L2 结论
  HIT=path:line:detail                          # 每个 L1 候选一行

退出码：0 干净 / 2 L1 命中候选 / 3 L2 复现崩溃 / 4 用法或 IO 错误。
"""
from __future__ import annotations

import argparse
import fnmatch
import os
import re
import subprocess
import sys
import tempfile

# ---------------------------------------------------------------- 常量

# 清理类函数名后缀（上游命名习惯，覆盖 C/C++ 常见约定）
CLEANUP_SUFFIX = (
    r"(?:cleanup|close|deactivate|destroy|free|shutdown|teardown|release)"
)

# 函数定义行：返回类型可选（上游普遍把返回类型与函数名分两行写）
CLEANUP_FUNC_RE = re.compile(
    r"^\s*(?:[A-Za-z_][\w \t\*]*[ \t\*]+)?"        # 可选返回类型
    r"([A-Za-z_][A-Za-z0-9_]*?" + CLEANUP_SUFFIX + r")\s*\(")

# 循环语句（C/C++：for/while）
LOOP_RE = re.compile(r"^\s*(?:for|while)\s*\(")

# 「解引用某个句柄」的调用形态：fn(x->handle, ...) 或 fn(handle, ...)
DEREF_CALL_RE = re.compile(
    r"\b[A-Za-z_][\w]*\s*\(\s*(?:[A-Za-z_][\w]*\s*->\s*)?([A-Za-z_][\w]*)\s*"
    r"(?:,\s*[^)]*)?\)"
)

# 句柄类字段名（惰性初始化对象，最容易被漏掉 NULL 检查）
HANDLE_FIELD_HINT = re.compile(
    r"instance|client|handle|server|connection|conn|display|device|stream|"
    r"context|session|port|world",
    re.IGNORECASE,
)

# 守卫写法：if (x->h) / if (x->h != NULL) / assert(x->h) / if (!x->h) return
GUARD_RE_TMPL = r"(?:if|while)\s*\(\s*[^)]*{field}[^)]*\)|assert\s*\(\s*[^)]*{field}"

# L2：服务/设备连接失败特征（可扩展；命中任一即可）
SERVICE_ABSENT_PATTERNS = (
    r"Failed to connect to audio system",
    r"Cannot connect to server",
    r"jack server is not running",
    r"Failed to connect to display",
    r"cannot open display",
    r"Connection refused",
    r"No such device",
    r"Could not connect to server",
    r"server is not running",
)

# L2：崩溃特征
CRASH_PATTERNS = (
    r"Segmentation fault",
    r"SIGSEGV",
    r"core dumped",
    r"signal 11",
)

SRC_GLOBS = ("*.c", "*.h", "*.cc", "*.cpp", "*.cxx", "*.hpp")


# ---------------------------------------------------------------- L1 源码扫描

def _iter_sources(root: str):
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs
                   if d not in (".git", "build", "build-release", "node_modules")]
        for name in files:
            if any(fnmatch.fnmatch(name, g) for g in SRC_GLOBS):
                yield os.path.join(base, name)


def _function_spans(lines):
    """粗粒度切分函数体：返回 [(name, start_idx, end_idx)]（0-based，含端点）。

    不追求完整语法树——只用来限定「清理函数内部」这个搜索窗口，误判由
    后续的循环/守卫判定收敛。
    """
    spans = []
    name, start = None, None
    depth = 0
    for i, line in enumerate(lines):
        if name is None:
            m = CLEANUP_FUNC_RE.match(line)
            if m:
                stripped = line.rstrip()
                # 函数定义：同行有 "{"，或签名跨行（本行以 ")" 结尾）。
                # 调用语句（以 ";" 结尾且无 "{"）不算定义。
                is_def = ("{" in line
                          or (stripped.endswith(")") and not stripped.endswith(";")))
                if not is_def:
                    continue
                name, start = m.group(1), i
                depth = line.count("{") - line.count("}")
                if depth <= 0 and "{" in line:
                    spans.append((name, start, i))
                    name = None
            continue
        depth += line.count("{") - line.count("}")
        if depth <= 0:
            spans.append((name, start, i))
            name = None
    if name is not None:
        spans.append((name, start, len(lines) - 1))
    return spans


def scan_source(root: str):
    """返回候选列表 [(path, lineno, detail)]。"""
    hits = []
    for path in _iter_sources(root):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
        except OSError:
            continue
        for fname, start, end in _function_spans(lines):
            body = lines[start:end + 1]
            # 只看真在清理语义函数里的循环
            for off, line in enumerate(body):
                if not LOOP_RE.match(line):
                    continue
                # 循环窗口 = 该行起 12 行内
                window = body[off:off + 12]
                text = "".join(window)
                for m in DEREF_CALL_RE.finditer(text):
                    field = m.group(1)
                    if not HANDLE_FIELD_HINT.search(field):
                        continue
                    guard_re = re.compile(GUARD_RE_TMPL.format(field=re.escape(field)))
                    if guard_re.search(text):
                        continue  # 已有守卫
                    lineno = start + off + 1
                    hits.append((path, lineno,
                                 f"{fname}(): loop derefs '{field}' without NULL guard"))
                    break
    return hits


# ---------------------------------------------------------------- L2 运行期

def analyse_log(text: str):
    """返回 (verdict, evidence)。verdict: 'yes' | 'no' | 'unknown'。"""
    service = next((p for p in SERVICE_ABSENT_PATTERNS if re.search(p, text)), None)
    crash = next((p for p in CRASH_PATTERNS if re.search(p, text, re.IGNORECASE)), None)
    if service and crash:
        return "yes", f"service_absent='{service}' + crash='{crash}'"
    if crash and not service:
        return "no", f"crash='{crash}' without service-absent signature"
    if service and not crash:
        return "no", f"service_absent='{service}' but no crash (graceful)"
    return "unknown", "neither signature present"


def run_and_capture(cmd: str, timeout: int):
    """跑命令并把输出落文件（绝不接管道，避免 SIGPIPE 干扰被测进程）。"""
    fd, path = tempfile.mkstemp(prefix="absent-service-", suffix=".log")
    os.close(fd)
    with open(path, "w", encoding="utf-8", errors="replace") as out:
        try:
            rc = subprocess.run(cmd, shell=True, stdout=out,
                                stderr=subprocess.STDOUT,
                                timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            rc = 124
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return rc, fh.read(), path


# ---------------------------------------------------------------- CLI

def _cmd_scan(args):
    hits = scan_source(args.src)
    print(f"SCAN_ROOT={os.path.abspath(args.src)}")
    for path, lineno, detail in hits[:args.max_hits]:
        print(f"HIT={path}:{lineno}:{detail}")
    print(f"HIT_COUNT={len(hits)}")
    print(f"ABSENT_SERVICE_CLEANUP_CANDIDATE={'yes' if hits else 'no'}")
    return 2 if hits else 0


def _cmd_runtime(args):
    if args.log:
        with open(args.log, "r", encoding="utf-8", errors="replace") as fh:
            text, rc, origin = fh.read(), args.rc, args.log
    else:
        rc, text, origin = run_and_capture(args.run, args.timeout)
        print(f"RUNTIME_LOG={origin}")
    verdict, evidence = analyse_log(text)
    # 崩溃退出码本身也算强证据（139 = 128+11）
    if verdict != "yes" and rc in args.crash_rc and evidence.startswith("crash="):
        verdict = "no"  # 无服务缺失特征，不归本类
    print(f"RUNTIME_EXIT_CODE={rc}")
    print(f"RUNTIME_EVIDENCE={evidence}")
    print(f"ABSENT_SERVICE_CRASH_CONFIRMED={verdict}")
    return 3 if verdict == "yes" else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_scan = sub.add_parser("scan", help="L1：扫描源码里的无守卫清理循环")
    p_scan.add_argument("--src", required=True, help="源码根目录")
    p_scan.add_argument("--max-hits", type=int, default=50)
    p_scan.set_defaults(func=_cmd_scan)

    p_run = sub.add_parser("runtime", help="L2：解析日志或直接跑命令")
    group = p_run.add_mutually_exclusive_group(required=True)
    group.add_argument("--log", help="已有日志文件")
    group.add_argument("--run", help="要执行的命令（输出自动落文件）")
    p_run.add_argument("--timeout", type=int, default=60)
    p_run.add_argument("--rc", type=int, default=None,
                       help="配合 --log 使用：该日志对应的进程退出码")
    p_run.add_argument("--crash-rc", type=int, nargs="*", default=[139],
                       help="视为崩溃的退出码，默认 139（SIGSEGV）")
    p_run.set_defaults(func=_cmd_runtime)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
