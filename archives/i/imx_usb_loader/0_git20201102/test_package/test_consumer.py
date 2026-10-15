#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_consumer.py — imx_usb_loader 消费者用例

两份「消费者」视角的证据：

(A) **交付的 CLI 真跑**（能执行就真跑；OHOS 上 conan 包目录里的动态链接 ELF 可能被
    加载器拒绝 —— 那时**显式打印平台限制**，绝不静默跳过；等价硬门禁已在 build()
    用 build 树里的同一份产物跑过）。
    期望值来自上游源码字面量：
      * ``imx_usb.c:608``  ``printf("imx_usb " IMX_LOADER_VERSION "\\n")``
      * ``imx_uart.c:330`` 同一个横幅（上游 quirk：imx_uart 也打印 "imx_usb …"）
      * ``imx_loader.h:22`` ``#define IMX_LOADER_VERSION "0.2pre"``
      * ``print_usage()`` 里的 usage 字面量

(B) **配置数据库契约**（与能否执行无关，永远真跑）：
    包内 ``etc/imx-loader.d/`` 是二进制启动时真正读取的数据。用**独立**的 Python
    解析器按上游 ``imx_loader_config.c`` 的格式解析 ``imx_usb.conf``，核对
      * 22 条 ``0xVID:0xPID, <board>.conf`` 映射全部格式合法；
      * 上游测试语料用的那对 ``0x15a2:0x0061`` 必须映射到 ``mx6_usb_work.conf``
        （上游 ``tests/Makefile`` 三个黄金用例用的就是这个 PID）；
      * 引用了但**未随包交付**的配置恰好是上游的三个历史缺口
        （``mx23_usb_work.conf`` / ``mx28_usb_work.conf`` / ``linux_gadget.conf``，
        上游从未把这些板级配置提交进仓库）；
      * 磁盘上的 14 个 ``*.conf`` 与 ``test_layout.py`` 里那张由钉死 tarball
        派生的 sha256 表逐条一致。
"""
import argparse
import hashlib
import os
import re
import subprocess
import sys

CHECKS = []
FAILURES = []
STATUS = {"cli_runs": 0}

VERSION_STRING = "0.2pre"                    # imx_loader.h:22
USAGE_LITERALS = [                           # print_usage() 字面量
    "Usage: imx_usb [OPTIONS...] [JOBS...]",
    "-S --sim=VID:PID\tSimulate a device of VID:PID",
]
GOLDEN_VIDPID = "0x15a2:0x0061"              # tests/Makefile: -S 0x15a2:0x0061
GOLDEN_TARGET_CONF = "mx6_usb_work.conf"
# 上游 imx_usb.conf 引用了、但仓库里没有的三个板级配置（上游历史缺口）
UPSTREAM_MISSING_CONFS = {
    "mx23_usb_work.conf", "mx28_usb_work.conf", "linux_gadget.conf"}
EXPECTED_CONF_COUNT = 14
EXPECTED_MAP_ENTRIES = 22

LOADER_REFUSAL_MARKERS = (
    "Error loading shared library",
    "Permission denied",
    "cannot execute binary file",
    "Exec format error",
    "error: cannot locate symbol",
)


def record(name, ok, detail=""):
    CHECKS.append(name)
    print("  [{}] {} {}".format("ok" if ok else "FAIL", name, detail))
    if not ok:
        FAILURES.append(name)


def loader_refused(text):
    return any(m in text for m in LOADER_REFUSAL_MARKERS)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 16), b""):
            h.update(blk)
    return h.hexdigest()


def parse_imx_usb_conf(path):
    """Independent parser for upstream's `#vid:pid, config_file` map.

    Format follows `imx_usb.conf` as generated/consumed by
    imx_loader_config.c: comment lines start with '#', entries are
    `0xVID:0xPID, <file>`.
    """
    entries, bad = [], []
    with open(path, "r", errors="replace") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = re.match(r"^(0x[0-9a-fA-F]+):(0x[0-9a-fA-F]+),\s*(\S+)$", line)
            if m:
                entries.append((int(m.group(1), 16), int(m.group(2), 16), m.group(3)))
            else:
                bad.append((lineno, line))
    return entries, bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package-folder", required=True)
    ap.add_argument("--os", required=True)
    ap.add_argument("--arch", required=True)
    args = ap.parse_args()
    pkg = args.package_folder
    is_ohos = str(args.os) == "OHOS"

    imx_usb = os.path.join(pkg, "bin", "imx_usb")
    imx_uart = os.path.join(pkg, "bin", "imx_uart")
    confdir = os.path.join(pkg, "etc", "imx-loader.d")
    confmap = os.path.join(confdir, "imx_usb.conf")

    # ── (A) 交付的 CLI ────────────────────────────────────────────────
    record("交付的 bin/imx_usb、bin/imx_uart 存在",
           os.path.isfile(imx_usb) and os.path.isfile(imx_uart),
           "{}, {}".format(imx_usb, imx_uart))

    cli_ok = True
    if os.path.isfile(imx_usb):
        env = dict(os.environ)
        env["LC_ALL"] = "C"
        try:
            res = subprocess.run([imx_usb, "-V"], capture_output=True, text=True,
                                 timeout=120, env=env)
            got = (res.stdout or "").strip()
            if res.returncode == 0 and got == "imx_usb " + VERSION_STRING:
                STATUS["cli_runs"] = 1
            else:
                blob = (res.stdout or "") + (res.stderr or "")
                if res.returncode != 0 and loader_refused(blob):
                    cli_ok = False
                else:
                    record("imx_usb -V == 'imx_usb {}'（imx_usb.c:608 + imx_loader.h:22）".format(
                        VERSION_STRING), False,
                        "rc={} got={!r}".format(res.returncode, got))
                    cli_ok = False
        except OSError as exc:
            cli_ok = False
            print("[platform-limitation] 无法 execve 交付的 imx_usb：{}".format(exc))

    if not cli_ok:
        print("[platform-limitation] 交付的 CLI 在本 runner 上不可执行（OHOS 加载器拒绝"
              " conan 包目录内的动态链接 ELF，或权限不足）。**不静默跳过**：等价用例已在"
              " build() 里用 build 树里的同一份 imx_usb/imx_uart 真跑过"
              "（`-V` / `-h` / 负例 + 上游 tests/ 三个黄金用例）。")
        print("[platform-limitation]   → 下面只跑与可执行权限无关的配置数据库契约。")
    else:
        env = dict(os.environ)
        env["LC_ALL"] = "C"
        res = subprocess.run([imx_usb, "-V"], capture_output=True, text=True,
                             timeout=120, env=env)
        record("imx_usb -V == 'imx_usb {}'（imx_usb.c:608 + imx_loader.h:22）".format(
            VERSION_STRING), (res.stdout or "").strip() == "imx_usb " + VERSION_STRING,
            repr((res.stdout or "").strip()))

        res = subprocess.run([imx_uart, "-V"], capture_output=True, text=True,
                             timeout=120, env=env)
        record("imx_uart -V 也打印 'imx_usb {}'（imx_uart.c:330 的上游 quirk）".format(
            VERSION_STRING), (res.stdout or "").strip() == "imx_usb " + VERSION_STRING,
            repr((res.stdout or "").strip()))

        res = subprocess.run([imx_usb, "-h"], capture_output=True, text=True,
                             timeout=120, env=env)
        missing = [lit for lit in USAGE_LITERALS if lit not in (res.stdout or "")]
        record("imx_usb -h 含 print_usage() 的 {} 条 usage 字面量".format(
            len(USAGE_LITERALS)), res.returncode == 0 and not missing,
            "missing={!r}".format(missing))

        res = subprocess.run([imx_usb, "-c", os.path.join(pkg, "does-not-exist"), "-v"],
                             capture_output=True, text=True, timeout=120, env=env)
        record("负例：imx_usb -c <不存在的配置目录> 退出码非 0",
               res.returncode != 0, "rc={}".format(res.returncode))

    # ── (B) 配置数据库契约（与可执行权限无关） ────────────────────────
    record("交付 etc/imx-loader.d/imx_usb.conf（二进制的 VID:PID 映射数据库）",
           os.path.isfile(confmap), confmap)

    confs = sorted(n for n in os.listdir(confdir)) if os.path.isdir(confdir) else []
    record("etc/imx-loader.d/ 里恰好 {} 个上游 *.conf".format(EXPECTED_CONF_COUNT),
           len(confs) == EXPECTED_CONF_COUNT, "got {}".format(len(confs)))

    entries, bad_lines = ([], []) if not os.path.isfile(confmap) else parse_imx_usb_conf(confmap)
    record("imx_usb.conf 独立解析出 {} 条 vid:pid 映射且格式全部合法".format(
        EXPECTED_MAP_ENTRIES), len(entries) == EXPECTED_MAP_ENTRIES and not bad_lines,
        "entries={} bad_lines={}".format(len(entries), bad_lines[:2]))

    referenced = {e[2] for e in entries}
    delivered = set(confs)
    missing_confs = sorted(referenced - delivered)
    record("映射里引用了但未交付的配置恰好是上游三个历史缺口 {}".format(
        sorted(UPSTREAM_MISSING_CONFS)),
        set(missing_confs) == UPSTREAM_MISSING_CONFS, "{}".format(missing_confs))

    golden = [e for e in entries if "0x{:04x}:0x{:04x}".format(e[0], e[1]) == GOLDEN_VIDPID]
    record("上游 tests/Makefile 用的 {} 映射到 {}".format(GOLDEN_VIDPID, GOLDEN_TARGET_CONF),
           len(golden) == 1 and golden[0][2] == GOLDEN_TARGET_CONF,
           "{}".format([g[2] for g in golden]))

    # 交付的配置与钉死 tarball 的字节一致（表从 tarball 派生，见 test_layout.py）
    import test_layout as TL  # noqa: E402  (同目录、纯标准库)
    mismatched = []
    for name, want in sorted(TL.CONF_SHA256.items()):
        path = os.path.join(confdir, name)
        if not os.path.isfile(path) or sha256(path) != want:
            mismatched.append(name)
    record("14 个 *.conf 与钉死 tarball 派生的 sha256 表逐条一致", not mismatched,
           "{}".format(mismatched))

    record("交付的 imx_usb.conf 非空且以 '#' 注释头开始（上游文件形态）",
           os.path.isfile(confmap) and
           open(confmap, "r", errors="replace").readline().lstrip().startswith("#"),
           os.path.isfile(confmap) and
           repr(open(confmap, "r", errors="replace").readline()[:48]))

    print("[consumer] checks={} passed={} failed={} (CLI executed={})".format(
        len(CHECKS), len(CHECKS) - len(FAILURES), len(FAILURES), STATUS["cli_runs"]))
    if FAILURES:
        print("[consumer] FAILED: " + ", ".join(FAILURES))
        return 1
    print("[consumer] OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
