#!/usr/bin/env python3
"""physlock/13 test_package 消费者测试。

上游**没有自动化测试**（无 tests/ 目录，Makefile 无 check/test 目标），因此本脚本覆盖：

  A. CLI 行为（上游 README 文档化的可执行样例入口，安全、不触发锁屏）
  B. OHOS 特有条目（ELF 目标架构 / OHOS musl 解释器 / `.codesign` 签名段）>= 1

用法: test_physlock.py <package_folder> <runtime:0|1>
"""
import os
import struct
import subprocess
import sys

PACKAGE = sys.argv[1]
RUNTIME = sys.argv[2] if len(sys.argv) > 2 else "0"
EXE = os.path.join(PACKAGE, "bin", "physlock")
MAN = os.path.join(PACKAGE, "share", "man", "man1", "physlock.1")

EM_AARCH64 = 183
PT_INTERP = 3
OHOS_MUSL_INTERP = "/lib/ld-musl-aarch64.so.1"

_passed = 0
_failed = []


def check(name, cond, detail=""):
    global _passed
    if cond:
        _passed += 1
        print(f"PASS {name}")
    else:
        _failed.append(name)
        print(f"FAIL {name}: {detail}")


def read_elf(path):
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:4] != b"\x7fELF":
        raise RuntimeError("not an ELF file")
    is64 = data[4] == 2
    little = data[5] == 1
    endian = "<" if little else ">"
    e_machine = struct.unpack_from(endian + "H", data, 18)[0]
    e_phoff = struct.unpack_from(endian + "Q", data, 32)[0]
    e_phentsize = struct.unpack_from(endian + "H", data, 54)[0]
    e_phnum = struct.unpack_from(endian + "H", data, 56)[0]
    interp = None
    if is64:
        for i in range(e_phnum):
            base = e_phoff + i * e_phentsize
            if struct.unpack_from(endian + "I", data, base)[0] == PT_INTERP:
                p_offset = struct.unpack_from(endian + "Q", data, base + 8)[0]
                p_filesz = struct.unpack_from(endian + "Q", data, base + 32)[0]
                interp = data[p_offset:p_offset + p_filesz].split(b"\x00")[0].decode()
                break
    return e_machine, interp


def run(args, expect_code=None, expect_text=None):
    result = subprocess.run([EXE, *args], stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, timeout=20)
    if expect_code is not None and result.returncode != expect_code:
        raise RuntimeError(f"{args} exit {result.returncode}: {result.stdout!r}")
    if expect_text and expect_text.lower() not in result.stdout.lower():
        raise RuntimeError(f"{args} output lacks {expect_text!r}: {result.stdout!r}")
    return result


# ------------------------------------------------------------------
# B. OHOS 特有条目（只读 ELF，始终执行，交叉构建也有效）—— 3 条
# ------------------------------------------------------------------
check("OHOS-01 physlock executable installed", os.path.isfile(EXE), EXE)

machine, interp = read_elf(EXE)
check("OHOS-02 ELF target is AArch64 (OHOS PC)", machine == EM_AARCH64,
      f"e_machine={machine}")
check("OHOS-03 OHOS musl dynamic interpreter", interp == OHOS_MUSL_INTERP,
      f"PT_INTERP={interp}")

with open(EXE, "rb") as fh:
    blob = fh.read()
check("OHOS-04 OHOS .codesign section present", b".codesign" in blob,
      "no .codesign section (OHOS refuses to run unsigned ELF)")

# ------------------------------------------------------------------
# A. 上游 CLI 行为（上游 README 文档化的样例入口）—— 3 条
# ------------------------------------------------------------------
if RUNTIME == "1":
    try:
        res = run(["-v"], expect_code=0, expect_text="physlock")
        check("CLI-01 `physlock -v` prints version 13", "13" in res.stdout, res.stdout)
    except Exception as exc:  # noqa: BLE001
        check("CLI-01 `physlock -v` prints version 13", False, str(exc))

    try:
        run(["-h"], expect_code=0, expect_text="usage: physlock")
        check("CLI-02 `physlock -h` prints usage and exits 0", True)
    except Exception as exc:  # noqa: BLE001
        check("CLI-02 `physlock -h` prints usage and exits 0", False, str(exc))

    try:
        res = run(["-Z"], expect_text="usage: physlock")
        check("CLI-03 invalid option prints usage and exits non-zero",
              res.returncode != 0, f"exit={res.returncode}")
    except Exception as exc:  # noqa: BLE001
        check("CLI-03 invalid option prints usage and exits non-zero", False, str(exc))
else:
    print("SKIP CLI-01/02/03: cross-build (cannot run target binary)")

# 打包完整性：man page 渲染（等价上游 make install 的 sed 处理）
check("PKG-01 rendered man page installed", os.path.isfile(MAN), MAN)
if os.path.isfile(MAN):
    with open(MAN, encoding="utf-8", errors="replace") as fh:
        man = fh.read()
    check("PKG-02 man page VERSION placeholder substituted",
          "VERSION" not in man, "man page still contains literal 'VERSION'")

total = _passed + len(_failed)
print(f"\nphyslock/13 test_package: {_passed}/{total} passed")
if _failed:
    print("failed: " + ", ".join(_failed))
    sys.exit(1)
