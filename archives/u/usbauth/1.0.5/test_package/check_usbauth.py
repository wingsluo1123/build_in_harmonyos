#!/usr/bin/env python3
"""消费测试 — usbauth 1.0.5 真实产物校验（全部离线，不触网）。

用法: python3 check_usbauth.py <package_folder>

说明：usbauth 由 udev 规则在设备接入时调用，正常功能需要 USB 设备与 udev/dbus 运行时；沙箱/CI 里
      不做真机设备验证，断言的是"产物可用 + 配置与规则随包"这一层。任何一项不成立即 fail。
"""
import hashlib
import os
import subprocess
import sys

checks = fails = skips = 0


def ok(msg):
    global checks
    checks += 1
    print("[ok]   %s" % msg)


def sk(msg):
    """环境原因导致本项无法判定：单独计入 skips，**不计入通过**。"""
    global checks, skips
    checks += 1
    skips += 1
    print("[skip] %s" % msg)


def fail(msg):
    global checks, fails
    checks += 1
    fails += 1
    print("[FAIL] %s" % msg)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    pkg = sys.argv[1]
    # 上游是 sbin_PROGRAMS → 优先 sbin，兼容 bin
    exe = None
    for rel in (os.path.join("sbin", "usbauth"), os.path.join("bin", "usbauth")):
        cand = os.path.join(pkg, rel)
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            exe = cand
            break

    # ① 产物
    if exe:
        ok("产物齐备：%s 存在且可执行（%d 字节）"
           % (os.path.relpath(exe, pkg), os.path.getsize(exe)))
    else:
        fail("缺少可执行产物：%s/{sbin,bin}/usbauth" % pkg)
        print("\nchecks=%d fails=%d skips=%d\nRESULT: FAIL" % (checks, fails, skips))
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

    # ③ 真跑（--help / --version / -h 任一成功即可；**能失败**的真断言）
    try:
        blob, rc = "", None
        for flag in ("--help", "--version", "-h"):
            r = subprocess.run([exe, flag], capture_output=True, text=True, timeout=300)
            blob = ((r.stdout or "") + (r.stderr or "")).strip()
            rc = r.returncode
            if rc == 0 and blob:
                break
        if rc == 0 and blob:
            ok("真实运行：`usbauth <flag>` rc=0 且有输出 ✓（首行：%s）"
               % blob.splitlines()[0][:70])
        else:
            fail("`usbauth --help/--version/-h` 均未成功（rc=%s）：%s" % (rc, blob[:250]))
    except Exception as exc:
        fail("usbauth 无法执行：%s" % str(exc)[:200])

    # ④ 配置与 udev 规则随包（上游 data/ 里就这两样东西）
    data = []
    for root, _, files in os.walk(pkg):
        for f in files:
            if f in ("usbauth.conf", "20-usbauth.rules"):
                data.append(os.path.relpath(os.path.join(root, f), pkg))
    if len(data) >= 2:
        ok("配置与 udev 规则随包 ✓（%s）" % ", ".join(sorted(data)))
    else:
        fail("配置/udev 规则未随包（找到：%s）" % (", ".join(data) or "无"))

    # ⑤ 许可证随包
    lic = os.path.join(pkg, "licenses", "COPYING")
    if os.path.isfile(lic):
        ok("许可证随包：licenses/COPYING 存在（GPL-2.0）")
    else:
        fail("缺少 licenses/COPYING")

    # ⑥ 证据
    try:
        h = hashlib.sha256(open(exe, "rb").read()).hexdigest()
        ok("证据：%s sha256=%s…；python %s"
           % (os.path.relpath(exe, pkg), h[:16], sys.version.split()[0]))
    except Exception as exc:
        fail("证据收集失败：%s" % str(exc)[:120])

    print("\nchecks=%d fails=%d skips=%d" % (checks, fails, skips))
    print("RESULT: %s" % ("PASS" if fails == 0 else "FAIL"))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
