#!/usr/bin/env python3
"""消费测试 — pesign 116 真实产物校验（全部离线，不触网）。

用法: python3 check_pesign.py <package_folder>

说明：pesign 用来给 PE/COFF（UEFI 应用、shim、内核等）签名与校验，真正签名需要 NSS 证书库与
      EFI 变量/固件环境；沙箱/CI 里不做真机签名验证，断言落在"产物可用 + 命令真跑得起来"这一层。
      任何一项不成立即 fail；只有环境原因才计入 skips（且不计入通过）。
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
    global checks, skips
    checks += 1
    skips += 1
    print("[skip] %s" % msg)


def fail(msg):
    global checks, fails
    checks += 1
    fails += 1
    print("[FAIL] %s" % msg)


def find_exe(pkg, name):
    for sub in ("bin", "sbin", "libexec"):
        p = os.path.join(pkg, sub, name)
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return None


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    pkg = sys.argv[1]
    exes = {n: find_exe(pkg, n) for n in ("pesign", "efikeygen")}

    # ① 产物
    missing = [n for n, p in exes.items() if not p]
    if not missing:
        ok("产物齐备：%s（%d / %d 字节）"
           % (", ".join("%s=%s" % (n, os.path.relpath(p, pkg)) for n, p in sorted(exes.items())),
              os.path.getsize(exes["pesign"]), os.path.getsize(exes["efikeygen"])))
    else:
        fail("缺少可执行产物：%s（包内 bin/、sbin/、libexec/ 都没找到）" % ", ".join(missing))
        print("\nchecks=%d fails=%d skips=%d\nRESULT: FAIL" % (checks, fails, skips))
        return 1

    # ② ELF 头自检（以主命令 pesign 为准）
    exe = exes["pesign"]
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

    # ③/④ 真跑两个命令（--help / -h 任一成功即可；能失败的真断言）
    for name in ("pesign", "efikeygen"):
        p = exes[name]
        try:
            blob, rc, used = "", None, ""
            for flag in ("--help", "-h"):
                r = subprocess.run([p, flag], capture_output=True, text=True, timeout=300)
                blob = ((r.stdout or "") + (r.stderr or "")).strip()
                rc, used = r.returncode, flag
                if rc == 0 and blob:
                    break
            if rc == 0 and blob:
                ok("真实运行：`%s %s` rc=0 且有输出 ✓（首行：%s）"
                   % (name, used, blob.splitlines()[0][:64]))
            else:
                fail("`%s --help/-h` 未成功（rc=%s）：%s" % (name, rc, blob[:220]))
        except Exception as exc:
            fail("%s 无法执行：%s" % (name, str(exc)[:180]))

    # ⑤ 许可证随包
    lic = None
    for cand in ("licenses/COPYING", "licenses/LICENSE", "licenses/COPYING.md"):
        if os.path.isfile(os.path.join(pkg, cand)):
            lic = cand
            break
    if lic:
        ok("许可证随包：%s 存在" % lic)
    else:
        fail("缺少 licenses/ 下的许可证文件（COPYING/LICENSE）")

    # ⑥ 证据
    try:
        h = hashlib.sha256(open(exe, "rb").read()).hexdigest()
        ok("证据：%s sha256=%s…；python %s" % (os.path.relpath(exe, pkg), h[:16], sys.version.split()[0]))
    except Exception as exc:
        fail("证据收集失败：%s" % str(exc)[:120])

    print("\nchecks=%d fails=%d skips=%d" % (checks, fails, skips))
    print("RESULT: %s" % ("PASS" if fails == 0 else "FAIL"))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
