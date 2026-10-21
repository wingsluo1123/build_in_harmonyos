#!/usr/bin/env python3
"""Conan test_package for iw 6.17 — 对**已安装的二进制**做真实断言。

用法: python3 test_iw.py <package_folder>

口径（与 manifest.yaml / notes.md / PR 正文三处同源）：
  上游注册用例数 N_static = 0（R51 六探针全 0 命中：无 tests/ 目录、
  无 TESTS=/check_PROGRAMS=、无 test*.c、无 ctest/add_test、无 *RUNTEST*、
  无 demo/examples；全树唯一 "test" 命中是 NL80211_CMD_TESTMODE 驱动命令）。
  Makefile 里唯一的 `check:` 目标是 `sparse -Wall cgcc` 静态分析 lint，不是
  测试套件，故两者都不作为上游套件执行，也不计入通过率。本文件是消费者断言
  面（N_consumer），逐条真实执行 install 后的 bin/iw。

平台能力边界（真机实测，如实断言而非放宽期望）：
  app 沙箱在**创建** socket(AF_NETLINK, SOCK_RAW, NETLINK_GENERIC=16) 时即返回
  EACCES(13)；而 NETLINK_ROUTE(0) 可创建、可 bind。iw 经 generic netlink 访问
  nl80211，故所有**需要内核回话**的子命令必然以
  "Failed to connect to generic netlink." 退出 rc=1。这是平台事实、不是配方
  缺陷，断言把该 rc 与文案**逐字固定**——平台一旦放开，A8/A9 会立刻翻红暴露。
"""
import os
import subprocess
import sys

ELF_MAGIC = b"\x7fELF"
EM_AARCH64 = 183
NETLINK_WALL_MSG = "Failed to connect to generic netlink."

_passed = 0
_failed = 0


def check(cond, label, detail=""):
    global _passed, _failed
    if cond:
        _passed += 1
        print("PASS: %s" % label)
    else:
        _failed += 1
        print("FAIL: %s | %s" % (label, detail))


def run(bin_path, args):
    p = subprocess.run([bin_path] + args, capture_output=True, text=True, timeout=60)
    return p.returncode, (p.stdout or ""), (p.stderr or "")


def main():
    pkg_dir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    bin_path = os.path.join(pkg_dir, "bin", "iw")

    # ── 产物面 ──────────────────────────────────────────────
    exists = os.path.isfile(bin_path)
    check(exists, "A1 bin/iw 存在", bin_path)
    if not exists:
        print("SUMMARY: %d passed, %d failed" % (_passed, _failed))
        return 1

    # 纯 Python 读 ELF 头（OHOS 沙箱无 file 命令，batsignal 同法）
    with open(bin_path, "rb") as f:
        hdr = f.read(20)
    check(hdr[:4] == ELF_MAGIC, "A2 bin/iw 是 ELF 文件", repr(hdr[:4]))
    e_machine = hdr[18] | (hdr[19] << 8)
    check(e_machine == EM_AARCH64, "A3 bin/iw 为 aarch64 (EM_AARCH64=183)",
          "e_machine=%d" % e_machine)

    # ── CLI 契约面（不碰内核，真实执行）────────────────────
    rc, out, err = run(bin_path, ["--version"])
    check(rc == 0 and out.strip() == "iw version 6.17",
          "A4 iw --version 输出 'iw version 6.17' 且 rc=0",
          "rc=%d out=%r" % (rc, out[:80]))

    rc, out, err = run(bin_path, [])
    check(rc == 0 and "Usage:" in out and "Commands:" in out,
          "A5 无参数打印 usage + 命令表 且 rc=0", "rc=%d" % rc)
    for token in ("dev", "phy", "scan"):
        check(token in out, "A6 命令表含顶层命令 '%s'" % token)

    rc, out, err = run(bin_path, ["help"])
    check(rc == 0 and "Usage:" in out and "Commands:" in out,
          "A7 iw help rc=0 且含 Usage:/Commands:", "rc=%d" % rc)

    # ── 平台能力边界（逐字固定，不放宽）─────────────────────
    rc, out, err = run(bin_path, ["dev"])
    blob = out + err
    check(rc == 1 and NETLINK_WALL_MSG in blob,
          "A8 iw dev 命中平台 generic-netlink 墙（rc=1 且逐字 '%s'）" % NETLINK_WALL_MSG,
          "rc=%d blob=%r" % (rc, blob[:120]))

    rc, out, err = run(bin_path, ["phy"])
    check(rc == 1 and NETLINK_WALL_MSG in (out + err),
          "A9 iw phy 同样命中 generic-netlink 墙 且 rc=1", "rc=%d" % rc)

    print("SUMMARY: %d passed, %d failed" % (_passed, _failed))
    return 0 if _failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
