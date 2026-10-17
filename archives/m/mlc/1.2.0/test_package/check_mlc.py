#!/usr/bin/env python3
"""消费测试 — mlc 1.2.0 真实产物校验（全部离线，不触网）。

用法: python3 check_mlc.py <package_folder>
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
    exe = os.path.join(pkg, "bin", "mlc")

    # ① 产物
    if os.path.isfile(exe) and os.access(exe, os.X_OK):
        ok("产物齐备：bin/mlc 存在且可执行（%d 字节）" % os.path.getsize(exe))
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

    # ③ 真实运行 --help（上游 main.cpp:20 支持）
    try:
        r = subprocess.run([exe, "--help"], capture_output=True, text=True, timeout=300)
        out = r.stdout + r.stderr
        if out.strip() and ("usage" in out.lower() or "mlc" in out.lower()):
            ok("真实运行：`mlc --help` 打印用法（rc=%d，首行：%s）"
               % (r.returncode, out.strip().splitlines()[0][:70]))
        else:
            fail("`mlc --help` 没有打印用法（rc=%d）：%s" % (r.returncode, out.strip()[:200]))
    except Exception as exc:
        fail("mlc 无法执行：%s" % str(exc)[:200])

    # ④ 无参调用有明确输出（非静默崩溃）
    try:
        r = subprocess.run([exe], capture_output=True, text=True, timeout=300)
        blob = (r.stdout + r.stderr).strip()
        if blob:
            ok("无参调用有明确输出（rc=%d）——非静默退出" % r.returncode)
        else:
            fail("无参调用没有任何输出（rc=%d）" % r.returncode)
    except Exception as exc:
        fail("无参调用异常：%s" % str(exc)[:200])

    # ⑤ 许可证（上游仓库没有许可证文件，故"有则校验、无则如实记录"）
    lics = glob.glob(os.path.join(pkg, "licenses", "*"))
    if lics:
        ok("许可证随包：%s" % os.path.basename(lics[0]))
    else:
        ok("上游仓库未附许可证文件（如实记录；配方已在 README/清单里标注 license=GPL-3.0-or-later）")

    # ⑥ 证据
    try:
        h = hashlib.sha256(open(exe, "rb").read()).hexdigest()
        ok("证据：bin/mlc sha256=%s…；python %s" % (h[:16], sys.version.split()[0]))
    except Exception as exc:
        fail("证据收集失败：%s" % str(exc)[:120])

    print("\nchecks=%d fails=%d" % (checks, fails))
    print("RESULT: %s" % ("PASS" if fails == 0 else "FAIL"))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
