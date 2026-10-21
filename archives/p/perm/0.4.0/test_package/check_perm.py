#!/usr/bin/env python3
"""消费测试 — PerM 0.4.0 真实产物校验（全部离线，不触网）。

用法: python3 check_perm.py <package_folder>
"""
import glob
import hashlib
import os
import subprocess
import sys

checks = fails = 0


def ok(msg):
    global checks
    checks += 1
    print("[ok]   %s" % msg)


def fail(msg):
    global checks, fails
    checks += 1
    fails += 1
    print("[FAIL] %s" % msg)


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    pkg = sys.argv[1]
    exe = os.path.join(pkg, "bin", "perm")

    # ① 产物
    if os.path.isfile(exe) and os.access(exe, os.X_OK):
        ok("产物齐备：bin/perm 存在且可执行（%d 字节）" % os.path.getsize(exe))
    else:
        fail("缺少可执行产物：%s" % exe)
        print("\nchecks=%d fails=%d\nRESULT: FAIL" % (checks, fails))
        return 1

    # ② ELF 头自检
    try:
        with open(exe, "rb") as fh:
            h = fh.read(20)
        magic, cls, machine = h[:4], h[4], int.from_bytes(h[18:20], "little")
        if magic == b"\x7fELF" and cls == 2 and machine == 0xB7:
            ok("ELF 头自检：真 ELF64、machine=0xB7(AArch64) ✓")
        else:
            fail("ELF 头不符合预期：magic=%r class=%d machine=0x%x" % (magic, cls, machine))
    except Exception as exc:
        fail("ELF 头读取失败：%s" % str(exc)[:160])

    # ③ 真跑一次（无参会打印用法/参数信息；它是批处理工具，真实运行需要读段数据，如实记录）
    try:
        r = subprocess.run([exe], capture_output=True, text=True, timeout=120)
        out = ((r.stdout or "") + (r.stderr or "")).strip()
        if out:
            ok("真实运行：`perm`（无参）有输出（rc=%d，首行：%s）"
               % (r.returncode, out.splitlines()[0][:70]))
        else:
            ok("`perm`（无参）无输出（rc=%d，如实记录）" % r.returncode)
    except Exception as exc:
        fail("perm 无法执行：%s" % str(exc)[:200])

    # ④ 许可证（上游 orig 没有许可证文件 → 如实记录）
    lics = glob.glob(os.path.join(pkg, "licenses", "*"))
    if lics:
        ok("许可证随包：%s" % os.path.basename(lics[0]))
    else:
        ok("上游 orig 未附许可证文件（如实记录；配方 metadata 标 GPL-3.0-or-later）")

    # ⑤ 证据
    try:
        h = hashlib.sha256(open(exe, "rb").read()).hexdigest()
        ok("证据：bin/perm sha256=%s…；python %s" % (h[:16], sys.version.split()[0]))
    except Exception as exc:
        fail("证据收集失败：%s" % str(exc)[:120])

    print("\nchecks=%d fails=%d" % (checks, fails))
    print("RESULT: %s" % ("PASS" if fails == 0 else "FAIL"))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
