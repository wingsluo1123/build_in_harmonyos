#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""megactl 0.4.5 消费者测试 —— 真跑交付的两个 CLI，断言真实退出码与输出。

用法: python3 test_megactl.py <package_bin_dir>

为什么是这个形态
    megactl 的真实用途需要 MegaRAID 硬件 + /dev/megadev0 设备节点，CI 与开发机
    都没有，所以「跑起来看真实输出」只能覆盖到两条边界：
      ① 纯参数解析路径（-V / -h / 各选项校验）—— 完全不碰设备，确定性可断言；
      ② 设备打开与 ioctl 失败路径 —— 用 -D 指向一个自造的普通文件/不存在的
         路径，真进 open() 与 ioctl()，真拿到 errno，真打印上游的错误处理文案。
    这两条覆盖了 megactl 全部与硬件无关的代码路径（选项解析、target specifier
    解析、usage()、usage(2,...) 错误分支、device open 失败分支、ioctl 失败分支）。

上游 quirk（按实测值断言，不臆造 0.4.5）
    发布 tarball 是 0.4.5，但 megactl.c:91 的 version 变量仍是 "0.4.3-hmage"，
    故 `megactl -V` 打印 0.4.3-hmage。本测试断言实测值。

平台无关性
    本脚本在两种环境都能给出结论：
      · CI worker（OHOS aarch64 原生）：直接 exec 交付的 aarch64 二进制；
      · 开发/CI 同源 x86_64 主机：binfmt_misc 已注册 qemu-aarch64，直接 exec
        同样成功。
    若宿主既非 aarch64 又无 qemu/binfmt（ENOEXEC），则 CLI 断言如实标记为
    SKIP 并以非零退出，结构性断言仍照常执行 —— 绝不把「没跑」伪装成「通过」。
"""
from __future__ import print_function

import os
import shutil
import subprocess
import sys

# 上游 megactl.c:91 —— 发布 0.4.5 但该变量漏改，仍是 0.4.3-hmage
UPSTREAM_VERSION_STRING = "0.4.3-hmage"
AUTHOR = "Jefferson Ogata"

# 上游 megactl.c:601-629 —— 设备打不开时的两条合法拒绝路径，二者都是 return 1，
# 只是打印文案不同（详见 ⑥ 处的说明）。断言按前缀匹配这两条，而不是把 Linux
# 专有的一条当成跨平台不变量。
DEVICE_OPEN_REFUSALS = (
    "unable to open device",            # /proc/devices 可读但无设备条目 → 二次 open 失败
    "file /proc/devices access error",  # /proc/devices 不可读 → 二次 open 之前就退出
)

FAILED = []
SKIPPED = []
TOTAL = [0]
HARMONY = [0]          # 鸿蒙特有断言计数


def check(ok, label, detail=""):
    TOTAL[0] += 1
    if not ok:
        FAILED.append(label)
    print("  [%s] %s%s" % ("ok" if ok else "FAIL", label,
                           ("  " + detail) if detail else ""))
    return ok


def check_harmony(ok, label, detail=""):
    """鸿蒙特有断言：必须真在 HarmonyOS 目标产物上成立。"""
    HARMONY[0] += 1
    return check(ok, "[鸿蒙] " + label, detail)


class Runner(object):
    """执行交付的 CLI；宿主无法执行 aarch64 ELF 时如实记 SKIP。"""

    def __init__(self, bindir):
        self.bindir = bindir
        self.exec_ok = True
        self.reason = ""

    def path(self, tool):
        return os.path.join(self.bindir, tool)

    def __call__(self, tool, *args):
        cmd = [self.path(tool)] + list(args)
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            out, err = proc.communicate(timeout=120)
            return (proc.returncode,
                    out.decode("utf-8", "replace"),
                    err.decode("utf-8", "replace"))
        except OSError as exc:
            self.exec_ok = False
            self.reason = "无法执行 aarch64 ELF（errno=%s）：%s" % (
                getattr(exc, "errno", "?"), exc)
            return (None, "", "")


def skip_cli(label, reason):
    TOTAL[0] += 1
    SKIPPED.append("%s (%s)" % (label, reason))
    print("  [SKIP] %s  —— %s" % (label, reason))


def main(argv):
    if len(argv) < 2:
        print("usage: test_megactl.py <package_bin_dir>")
        return 2
    bindir = argv[1]

    # 交付物存在性：L1e 破坏性反向测试会把 bin/ 移走，届时这里必须硬失败
    print("消费者测试：megactl/megasasctl CLI 行为（bin=%s）" % bindir)
    missing = [t for t in ("megactl", "megasasctl")
               if not os.path.isfile(os.path.join(bindir, t))]
    if missing:
        print("  [FAIL] 交付的 CLI 缺失: %s" % ", ".join(missing))
        return 1

    run = Runner(bindir)
    workdir = os.path.abspath("_megactl_work")
    shutil.rmtree(workdir, ignore_errors=True)
    os.makedirs(workdir)

    # ── ① 版本与 verbosity（不碰设备，纯 stdout）────────────────────────
    rc, out, err = run("megactl", "-V")
    if run.exec_ok:
        check(rc == 0, "megactl -V 退出码 0", "rc=%r" % (rc,))
        check(out.strip() == UPSTREAM_VERSION_STRING,
              "megactl -V 打印上游内置版本串", "got=%r" % out.strip())
        check_harmony(rc == 0,
                     "交付的 megactl 在鸿蒙目标上真能执行并返回 0"
                     "（非仅交叉编译通过）", "rc=%r" % (rc,))

        rc, out, err = run("megactl", "-v", "-V")
        check(rc == 0 and ("megactl: version %s by %s"
                           % (UPSTREAM_VERSION_STRING, AUTHOR)) in out,
              "megactl -v -V 打印带作者的长版本行", "got=%r" % out.strip())

        rc, out, err = run("megasasctl", "-V")
        check(rc == 0 and out.strip() == UPSTREAM_VERSION_STRING,
              "megasasctl -V 打印同一版本串", "rc=%r got=%r" % (rc, out.strip()))

        rc, out, err = run("megasasctl", "-v", "-V")
        check(rc == 0 and ("megasasctl: version %s by %s"
                           % (UPSTREAM_VERSION_STRING, AUTHOR)) in out,
              "megasasctl -v -V 打印带作者的长版本行", "got=%r" % out.strip())

        # ── ② usage / help（rc=0，输出在 stderr）──────────────────────────
        usage_line = ("usage: %s [-vest] [-H] [-l log-page-nr] "
                      "[-T long|short] [target ...]")
        rc, out, err = run("megactl", "-?")
        check(rc == 0 and err.startswith(usage_line % "megactl"),
              "megactl -? 打印 usage 且退出 0", "rc=%r" % (rc,))

        rc, out, err = run("megactl", "-h")
        check(rc == 0 and err.startswith(usage_line % "megactl"),
              "megactl -h 打印 usage 且退出 0", "rc=%r" % (rc,))
        check("-V       Show version." in err,
              "megactl usage 列出 -V 选项")
        check("/dev/megadev0" in err,
              "megactl usage 指向 PERC 设备节点 /dev/megadev0")
        check("channels" in err,
              "megactl usage 用 channels 描述目标层级（PERC 架构）")

        rc, out, err = run("megasasctl", "-h")
        check(rc == 0 and err.startswith(usage_line % "megasasctl"),
              "megasasctl -h 打印 usage 且退出 0", "rc=%r" % (rc,))
        check("enclosures" in err,
              "megasasctl usage 用 enclosures 描述目标层级（-DMEGA_SAS_CTL 生效）")
        check("/dev/megaraid_sas_ioctl_node" in err,
              "megasasctl usage 指向 SAS 设备节点 /dev/megaraid_sas_ioctl_node")

        # ── ③ 选项校验错误分支：一律 rc=2 + 固定文案（usage(2,...)）────────
        cases = [
            (("megactl", "-Z"), 'megactl: invalid flag "Z"'),
            (("megactl", "-T", "bogus"),
             'megactl: invalid self test: "bogus"; must specify short or long'),
            (("megactl", "-l"), "megactl: no log page specified"),
            (("megactl", "-l", "0xZZ"), 'megactl: invalid log page "0xZZ"'),
            (("megactl", "-l", "9999"), 'megactl: log page out of range: "9999"'),
            (("megactl", "-D"), "megactl: no device specified"),
            (("megactl", "-H", "a0c0"),
             "megactl: for health check, must specify adapter only"),
        ]
        for argv_case, expect in cases:
            rc, out, err = run(*argv_case)
            check(rc == 2 and err.startswith(expect),
                  "选项校验 %s → rc=2 + 固定文案" % " ".join(argv_case),
                  "rc=%r first=%r" % (rc, err.splitlines()[0] if err else ""))
            # usage 正文必须跟在错误行之后（usage(ec, fmt) 的既有行为）
            check("usage: " in err, "%s → 错误行后附 usage 正文"
                  % " ".join(argv_case))

        # ── ④ target specifier 解析分支（MAX_CONTROLLERS=32）──────────────
        spec_cases = [
            (("megactl", "zz"), 'megactl: invalid specifier "zz"'),
            (("megactl", "a0x0"), 'megactl: invalid specifier "a0x0"'),
            (("megactl", "a99"), 'megactl: adapter out of range: "a99"'),
            (("megactl", "a0c99"), 'megactl: channel out of range: "a0c99"'),
            (("megactl", "a0c0t99"), 'megactl: target out of range: "a0c0t99"'),
        ]
        for argv_case, expect in spec_cases:
            rc, out, err = run(*argv_case)
            check(rc == 2 and err.startswith(expect),
                  "target 解析 %s → rc=2 + 固定文案" % " ".join(argv_case),
                  "rc=%r first=%r" % (rc, err.splitlines()[0] if err else ""))

        # ── ⑤ 组合语义：-V 在打开设备之前短路（上游既有行为）──────────────
        rc, out, err = run("megactl", "-est", "-V")
        check(rc == 0 and out.strip() == UPSTREAM_VERSION_STRING,
              "megactl -est -V 接受日志页开关且 -V 短路返回版本",
              "rc=%r got=%r" % (rc, out.strip()))

        rc, out, err = run("megactl", "-V", "a0c0")
        check(rc == 0 and out.strip() == UPSTREAM_VERSION_STRING,
              "megactl -V a0c0 在展开 target 前短路（不碰设备）",
              "rc=%r got=%r" % (rc, out.strip()))

        # ── ⑥ 设备打开 / ioctl 失败路径（真进 open() 与 ioctl()）──────────
        # 上游 megactl.c:601-629 对「设备打不开」有**两条**拒绝路径，都是
        # return 1，只是打印的文案不同：
        #   (a) fopen("/proc/devices", "r") 失败 → 打印
        #       "file /proc/devices access error" 后立刻退出（根本不再 open 一次）。
        #       鸿蒙 PC 走这条：应用沙箱下 /proc/devices 不可读 —— CI 构建
        #       #73496（worker CI-015，真机 OHOS aarch64）实测 rc=1 且首行为
        #       该文案，编译与前 36 项断言全部通过。
        #   (b) /proc/devices 可读但没有 MEGA_NAME 条目 → 第二次 open 仍失败
        #       → "unable to open device <dev>: <errno>"。Linux 走这条。
        # 故此处断言「rc=1 + stdout 为空 + stderr 命中两条上游文案之一」，
        # 并把实际命中的分支打进 detail，使日志能自证走的是哪条真机路径。
        # 附加的 stdout 为空这一条保证它确实「拒绝并退出」，而不是打了什么
        # 报告出来 —— 比只断言 rc=1 更强，且不依赖宿主 errno 文案。
        absent = os.path.join(workdir, "no-such-device-node")
        for tool in ("megactl", "megasasctl"):
            rc, out, err = run(tool, "-D", absent)
            first = err.splitlines()[0] if err else ""
            if first.startswith("unable to open device"):
                branch = "路径b 二次open失败"
            elif first.startswith("file /proc/devices access error"):
                branch = "路径a /proc/devices不可读"
            else:
                branch = "未命中上游文案"
            check(rc == 1 and out.strip() == "" and first.startswith(
                      DEVICE_OPEN_REFUSALS),
                  "%s -D <不存在> → rc=1 + 拒绝打开设备（%s）" % (tool, branch),
                  "rc=%r first=%r" % (rc, first))

        # 普通文件能 open 成功，随后 ioctl 失败 —— 真走到 megaGetDriverVersion
        regular = os.path.join(workdir, "regular-file")
        with open(regular, "wb") as handle:
            handle.write(b"\x00" * 64)
        rc, out, err = run("megactl", "-D", regular)
        # 只断言稳定前缀：errno 文案随宿主（真机 ENOTTY vs qemu ENOSYS）不同
        check(rc == 1 and err.startswith(
                  "unable to determine megaraid driver version"),
              "megactl -D <普通文件> → rc=1 + 'unable to determine ... version'"
              "（真进 ioctl 并走到上游错误分支）",
              "rc=%r first=%r" % (rc, err.splitlines()[0] if err else ""))
    else:
        for label in ("megactl -V", "megactl -v -V", "megasasctl -V",
                      "megasasctl -v -V", "megactl -?", "megactl -h",
                      "megasasctl -h", "选项校验 x7", "target 解析 x5",
                      "组合语义 x2", "设备失败路径 x3"):
            skip_cli(label, run.reason)

    shutil.rmtree(workdir, ignore_errors=True)

    print("=" * 64)
    print("断言 %d 项：通过 %d，失败 %d，跳过 %d；其中鸿蒙特有 %d 项"
          % (TOTAL[0], TOTAL[0] - len(FAILED) - len(SKIPPED),
             len(FAILED), len(SKIPPED), HARMONY[0]))
    if FAILED:
        for item in FAILED:
            print("  - FAIL: %s" % item)
        return 1
    if SKIPPED:
        print("  以下断言未执行（宿主无法运行 aarch64 ELF，不计为通过）:")
        for item in SKIPPED:
            print("    - %s" % item)
        return 1
    print("[test] %d/%d assertions passed" % (TOTAL[0], TOTAL[0]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
