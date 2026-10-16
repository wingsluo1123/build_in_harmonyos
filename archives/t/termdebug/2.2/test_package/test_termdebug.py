#!/usr/bin/env python3
"""termdebug/2.2 consumer test.

两段：
  A 静态段（交叉构建与真机都跑）
    包内容 / 5 个 argv[0] symlink / ELF64-AArch64 / man page / doc /
    "五个可选能力是否真的链进去了"的符号检查 / 无 x86-64 预编译残留
  B 运行段（目标可执行时）
    6 个 --help / 5 个 -V / 直接运行 termdebug 的分派拒绝消息。
    tdreplay --help 里的 --visual-compare、--picture=、--picture-series= 是按
    HAVE_CURSES+HAVE_UNISTRING / HAVE_CAIRO / HAVE_CAIRO+HAVE_PTHREAD 条件编译的，
    所以 --help 本身就是最便宜、最可靠的能力探针。

用法: python3 test_termdebug.py <package_folder> [--runtime]

--runtime 由 test_package/conanfile.py 按 can_run() 决定是否传。不传时只跑静态段
（并明确打印 SKIP 原因），绝不把"没跑"说成"通过"。
"""

import os
import struct
import subprocess
import sys

COMMANDS = ("tdrecord", "tdreplay", "tdrerecord", "tdview", "tdcompare")
MAN_PAGES = ("termdebug.1", "tdrecord.1", "tdreplay.1", "tdrerecord.1",
             "tdview.1", "tdcompare.1")
DOC_FILES = ("README", "COPYING", "Changelog")

# 每个可选能力 → 必须出现在最终 ELF 里的代表符号（符号名以字面量存在于
# .symtab/.dynstr，所以直接扫字节，不依赖 nm/llvm-nm，真机没有也能跑）。
# 取值来自 src/*.c 的实际调用：
#   src/curses_handling.c  -> setupterm / tigetstr / putp
#   src/window.c           -> uc_width
#   src/write_stringlist.c -> uc_is_general_category_withtable
#   src/write_image.c      -> cairo_* + pango_*
#   src/picture_queue.c    -> pthread_create
FEATURE_SYMBOLS = (
    ("curses (terminfo)", "setupterm"),
    ("libunistring (char width)", "uc_width"),
    ("libunistring (categories)", "uc_is_general_category_withtable"),
    ("cairo (image surface)", "cairo_image_surface_create"),
    ("cairo (png output)", "cairo_surface_write_to_png"),
    ("pangocairo (text layout)", "pango_cairo_create_layout"),
    ("pthread (picture series)", "pthread_create"),
)

# tdreplay --help 里按 HAVE_* 条件编译出来的能力开关
HELP_PROBES = (
    ("curses+libunistring (visual compare)", "-v, --visual-compare"),
    ("cairo (picture output)", "-p<name>, --picture=<name>"),
    ("cairo+pthread (picture series)", "-P<name>, --picture-series=<name>"),
)

# tdrecord / tdrerecord 是终端录制工具。上游在**没有控制终端**时会在处理选项之前
# 就拒绝运行（src/record.c:102 `fatal("Can only record from terminal devices\n")`），
# 所以 --help / -V 既不会打印用法块、退出码也不是 0。CI worker 没有 tty（CI #93683
# 实测 3 条断言因此假失败），这里按环境分别断言**真实行为**，而不是把断言放宽成恒真。
# 只有 tdrecord 有终端门槛：上游 src/record.c:101 `if (!isatty(STDIN_FILENO))
# fatal("Can only record from terminal devices\n");`，而且它发生在 parse_options 之前。
# tdrerecord 是「从已有录制再录一次」，**不需要**终端（CI #93695 实测其 -V/--help 均 exit 0），
# 所以它不属于这一类 —— 上一条提交把它一并算进来是我判错了。
RECORDING_COMMANDS = ("tdrecord",)
NO_TTY_MESSAGE = "Can only record from terminal devices"


def has_controlling_terminal():
    """当前进程是否有控制终端（CI 上没有）。"""
    try:
        fd = os.open("/dev/tty", os.O_RDWR)
    except OSError:
        return False
    os.close(fd)
    return True


HAS_TTY = has_controlling_terminal()

USAGE_LINES = {
    "tdrecord": "Usage: tdrecord [OPTIONS] <client> [<client options>]",
    "tdreplay": "Usage: tdreplay [OPTIONS] <recording>",
    "tdrerecord": "Usage: tdrerecord [OPTIONS] <recording>",
    "tdview": "Usage: tdview [OPTIONS] <recording>",
    "tdcompare": "Usage: tdcompare [OPTIONS] <recording A> <recording B>",
}

STATE = {"passed": [], "failed": [], "skipped": []}

# 有/无控制终端会改变 tdrecord/tdrerecord 的**预期行为**，日志里必须写明。
print("environment: controlling terminal = %s" % ("yes" if HAS_TTY else "no"))


def ok(name):
    STATE["passed"].append(name)
    print("PASS: %s" % name)


def bad(name, detail):
    STATE["failed"].append((name, detail))
    print("FAIL: %s\n      %s" % (name, detail))


def check(name, condition, detail=""):
    if condition:
        ok(name)
    else:
        bad(name, detail or "condition is false")


def skip(name, detail):
    STATE["skipped"].append((name, detail))
    print("SKIP: %s (%s)" % (name, detail))


def run(args, timeout=60):
    """执行命令；目标不可执行时返回 (None, 原因)。"""
    try:
        proc = subprocess.run(args, capture_output=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        return None, "%s: %s" % (type(exc).__name__, exc)
    out = (proc.stdout + proc.stderr).decode("utf-8", errors="replace")
    return proc.returncode, out


# ── A 静态段 ─────────────────────────────────────────────────────────

def test_binary_present(binary):
    check("bin/termdebug exists and is a regular file",
          os.path.isfile(binary) and not os.path.islink(binary), binary)
    check("bin/termdebug is executable", os.access(binary, os.X_OK), binary)


def test_symlinks(bin_dir):
    for command in COMMANDS:
        link = os.path.join(bin_dir, command)
        if not os.path.islink(link):
            kind = "missing" if not os.path.exists(link) else "regular file"
            bad("bin/%s is a symlink to termdebug" % command,
                "%s is not a symlink (%s)" % (link, kind))
            continue
        target = os.readlink(link)
        check("bin/%s is a symlink to termdebug" % command, target == "termdebug",
              "readlink=%r" % target)


def test_elf_header(binary):
    try:
        with open(binary, "rb") as handle:
            head = handle.read(20)
    except OSError as exc:
        bad("bin/termdebug is ELF64 little-endian AArch64", str(exc))
        return
    if head[:4] != b"\x7fELF" or len(head) < 20:
        bad("bin/termdebug is ELF64 little-endian AArch64",
            "bad ELF header %r" % head[:20])
        return
    ei_class, ei_data = head[4], head[5]
    machine = struct.unpack_from("<H", head, 18)[0]
    problems = []
    if ei_class != 2:
        problems.append("EI_CLASS=%d (want 2 = ELF64)" % ei_class)
    if ei_data != 1:
        problems.append("EI_DATA=%d (want 1 = little-endian)" % ei_data)
    if machine != 0xB7:
        problems.append("e_machine=0x%X (want 0xB7 = EM_AARCH64)" % machine)
    check("bin/termdebug is ELF64 little-endian AArch64", not problems,
          "; ".join(problems))


def test_man_pages(package):
    man_dir = os.path.join(package, "share", "man", "man1")
    for page in MAN_PAGES:
        path = os.path.join(man_dir, page)
        check("man page share/man/man1/%s" % page,
              os.path.isfile(path) and os.path.getsize(path) > 0, path)


def test_docs(package):
    doc_dir = os.path.join(package, "share", "doc", "termdebug")
    for name in DOC_FILES:
        path = os.path.join(doc_dir, name)
        check("doc share/doc/termdebug/%s" % name,
              os.path.isfile(path) and os.path.getsize(path) > 0, path)


def test_feature_symbols(binary):
    with open(binary, "rb") as handle:
        blob = handle.read()
    for feature, symbol in FEATURE_SYMBOLS:
        needle = symbol.encode()
        check("symbol %s present (%s)" % (symbol, feature), needle in blob,
              "symbol %s not found in bin/termdebug -- upstream configure "
              "silently degraded the build and the recipe's OPTOBJECTS "
              "assertion should have caught it" % symbol)


def test_no_stray_x86_elf(package):
    """上游 tarball 混进的 2013 年 x86-64 预编译残留不能出现在包里。"""
    offenders = []
    for root, _dirs, files in os.walk(package):
        for name in files:
            path = os.path.join(root, name)
            if os.path.islink(path):
                continue
            try:
                with open(path, "rb") as handle:
                    head = handle.read(20)
            except OSError:
                continue
            if head[:4] == b"\x7fELF" and len(head) >= 20:
                if struct.unpack_from("<H", head, 18)[0] == 0x3E:
                    offenders.append(os.path.relpath(path, package))
    check("no stray x86-64 ELF in the package", not offenders,
          "found: %s" % ", ".join(offenders))


# ── B 运行段 ─────────────────────────────────────────────────────────

def test_help(bin_dir):
    for command in COMMANDS:
        code, out = run([os.path.join(bin_dir, command), "--help"])
        if code is None:
            skip("%s --help" % command, out)
            continue
        if command in RECORDING_COMMANDS and not HAS_TTY:
            check("%s --help is refused with the documented no-terminal message"
                  % command,
                  code != 0 and NO_TTY_MESSAGE in out,
                  "exit=%s output=%r" % (code, out[:300]))
            continue
        expected = USAGE_LINES[command]
        check("%s --help prints its argv[0]-dispatched usage" % command,
              code == 0 and expected in out,
              "exit=%s; expected %r in output:\n%s" % (code, expected, out[:800]))


def test_help_probes(bin_dir):
    for feature, flag in HELP_PROBES:
        code, out = run([os.path.join(bin_dir, "tdreplay"), "--help"])
        if code is None:
            skip("help probe %s" % feature, out)
            continue
        check("help probe %s: tdreplay --help offers %r" % (feature, flag),
              flag in out,
              "option %r absent, so the matching HAVE_* macro was not compiled "
              "in:\n%s" % (flag, out[:1000]))


def test_version(bin_dir):
    for command in COMMANDS:
        code, out = run([os.path.join(bin_dir, command), "-V"])
        if code is None:
            skip("%s -V" % command, out)
            continue
        if command in RECORDING_COMMANDS and not HAS_TTY:
            check("%s -V is refused with the documented no-terminal message"
                  % command,
                  code != 0 and NO_TTY_MESSAGE in out,
                  "exit=%s output=%r" % (code, out[:300]))
            continue
        check("%s -V prints version and copyright" % command,
              code == 0 and "Copyright (C)" in out and "2.2" in out,
              "exit=%s output=%r" % (code, out[:300]))


def test_direct_invocation(bin_dir, binary):
    """直接跑 ELF（不叫 symlink 名）应提示改用 5 个命令名。"""
    code, out = run([binary])
    if code is None:
        skip("direct termdebug invocation", out)
        return
    check("direct termdebug invocation points at the 5 command names",
          code == 0 and "tdrecord" in out and "tdcompare" in out,
          "exit=%s output=%r" % (code, out[:300]))


def main():
    argv = [a for a in sys.argv[1:] if a != "--runtime"]
    runtime = "--runtime" in sys.argv[1:]
    if len(argv) != 1:
        print(__doc__)
        return 2
    package = os.path.abspath(argv[0])
    bin_dir = os.path.join(package, "bin")
    binary = os.path.join(bin_dir, "termdebug")
    if not os.path.isdir(bin_dir):
        print("FAIL: %s is not a directory" % bin_dir)
        return 1

    test_binary_present(binary)
    test_symlinks(bin_dir)
    test_elf_header(binary)
    test_man_pages(package)
    test_docs(package)
    test_feature_symbols(binary)
    test_no_stray_x86_elf(package)

    if runtime:
        test_help(bin_dir)
        test_help_probes(bin_dir)
        test_version(bin_dir)
        test_direct_invocation(bin_dir, binary)
    else:
        skip("runtime leg (6x --help, 3 help probes, 5x -V, direct invocation)",
            "cross build: can_run()=False, so the target ELF is only verified "
            "statically here; the runtime leg runs on the OHOS CI device")

    passed, failed, skipped = STATE["passed"], STATE["failed"], STATE["skipped"]
    print("\n" + "-" * 62)
    print("termdebug/2.2 consumer test: %d passed, %d failed, %d skipped"
          % (len(passed), len(failed), len(skipped)))
    for name, detail in skipped:
        print("  SKIPPED %s: %s" % (name, detail))
    for name, detail in failed:
        print("  FAILED  %s: %s" % (name, detail))
    if failed:
        return 1
    if not passed:
        print("ERROR: zero assertions ran -- vacuous test, refusing to pass")
        return 1
    print("L_RESULT=pass: %d/%d assertions" % (len(passed), len(passed)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
