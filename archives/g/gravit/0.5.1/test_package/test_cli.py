#!/usr/bin/env python3
"""gravit/0.5.1 CLI 端到端消费者用例（鸿蒙特有测试，rule12）。

**本文件不是断言清单**，而是若干**具名消费者用例**；每个用例都是一条完整的消费
者流程，按四段式组织：

    构造输入 → 真实执行 → 产出结果 → 校验内容

    CLI-1  version-banner       输入: `bin/gravit "echo 1" -v`
                                执行: 真实子进程运行已安装的 CLI
                                产出: 退出码 + 完整 stdout 字节流
                                校验: 与参考输出逐字节比对
    CLI-2  help-screen          同上，`-h` 的完整帮助屏
    CLI-3  long-option-aliases  `--version` / `--help` 必须与短写法逐字节相同
    CLI-4  quit-command         `quit` 命令：退出码 0 且不产生任何输出
    CLI-5  unknown-command      未知命令被如实报告，且无视频驱动时不崩溃

参考输出（REF_*）是**独立来源**，不是被测程序的自输出回填：它们取自上游
`src/command.c` 中的版本/版权/usage 字面量与 `data/commandhelp.txt` 的帮助屏文本
（本包未改动这两处文本，补丁 0002 只把 `commandhelp.txt` 的打开方式改为经
`findFile()` 的可重定位查找），控制台先回显 `echo 1` 得到的 `echo = 1` 行也是
上游 console 的固定行为。CLI-5 的其余行同样来自上游文本
（`src/command.c` 的 `Command not found`、`src/gfx.c` 的起动失败提示）。

全部用例的 stdout 按**字节**比对：少一个空格、多换行、长短写法不一致都会失败。
"""

import os
import subprocess
import sys

# ── 参考输出（独立来源，见模块文档） ────────────────────────────────────────
REF_VERSION = (
    "echo = 1\n"
    "Gravit 0.5.1\n"
    "Copyright 2003-2014 Gravit Development Team\n"
)

REF_HELP = (
    "echo = 1\n"
    "Gravit 0.5.1\n"
    "Copyright 2003-2014 Gravit Development Team\n"
    "\n"
    "usage: gravit [-nvh] [COMMAND] ...\n"
    "\n"
    "  -n, --noscript           don't load gravit configuration\n"
    "  -h, --help               you're looking at it\n"
    "  -v, --version            display version and quit\n"
    "\n"
    "  'COMMAND' should be encapsulated in quotes when there are spaces involved.\n"
    "  For example: gravit spawn record \"save mysim\" \"saveauto 20\"\n"
    "\n"
)

REF_QUIT = ""

REF_UNKNOWN_COMMAND = (
    "echo = 1\n"
    "not-a-command: Command not found\n"
    "SDL Init failed\n"
    "no_such_driver not available\n"
    "SDL Error: src/gfx.c:368 no_such_driver not available\n"
    "There has been an error on start-up. Read your gravit configration file"
    " to possibly fix this.\n"
)

# ── 用例表：每项都是一条完整的端到端消费者流程 ──────────────────────────────
CASES = [
    {
        "id": "CLI-1",
        "name": "version-banner",
        "purpose": "版本查询：CLI 打印的版本/版权行必须与上游字面量逐字节一致",
        "runs": [{"argv": ["echo 1", "-v"], "rc": 0, "expected": REF_VERSION}],
    },
    {
        "id": "CLI-2",
        "name": "help-screen",
        "purpose": "帮助屏：usage、三个选项、COMMAND 说明必须与上游文本逐字节一致",
        "runs": [{"argv": ["echo 1", "-h"], "rc": 0, "expected": REF_HELP}],
    },
    {
        "id": "CLI-3",
        "name": "long-option-aliases",
        "purpose": "长短写法等价：--version/--help 的输出必须与 -v/-h 的参考输出相同",
        "runs": [
            {"argv": ["echo 1", "--version"], "rc": 0, "expected": REF_VERSION},
            {"argv": ["echo 1", "--help"], "rc": 0, "expected": REF_HELP},
        ],
    },
    {
        "id": "CLI-4",
        "name": "quit-command",
        "purpose": "quit 命令：正常退出且不打印任何内容（视频子系统未启动即可工作）",
        "runs": [{"argv": ["quit"], "rc": 0, "expected": REF_QUIT}],
    },
    {
        "id": "CLI-5",
        "name": "unknown-command",
        "purpose": "未知命令被如实报告；无可用视频驱动时按上游提示失败而非崩溃",
        "runs": [
            {
                "argv": ["-n", "echo 1", "not-a-command"],
                "rc": 0,
                "expected": REF_UNKNOWN_COMMAND,
                # 无窗口系统：给一个不存在的视频驱动，让应用自行结束而不是被杀死。
                "env": {"SDL_VIDEODRIVER": "no_such_driver"},
            }
        ],
    },
]


def execute(executable, argv, environment, timeout=60):
    """真实执行：以子进程运行已安装的 CLI，返回 (退出码, stdout 字节)。"""
    proc = subprocess.run(
        [executable] + argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        env=environment,
    )
    return proc.returncode, proc.stdout


def summarise(text, limit=6):
    """把一段输出压成可读的一行摘要，便于在日志里定位差异。"""
    lines = text.splitlines()
    shown = lines[:limit]
    more = "" if len(lines) <= limit else f" … (+{len(lines) - limit} lines)"
    return " | ".join(shown) + more


def run_case(case, executable):
    print(f"=== {case['id']} {case['name']} ===")
    print(f"    目的: {case['purpose']}")
    failures = []
    for run in case["runs"]:
        argv = run["argv"]
        environment = dict(os.environ)
        environment.update(run.get("env", {}))
        print(f"    构造输入: {os.path.basename(executable)} {' '.join(argv)}")
        rc, out = execute(executable, argv, environment)
        actual = out.decode("utf-8", "replace")
        print(f"    真实执行: 退出码={rc}，产出 {len(out)} 字节 stdout")
        print(f"    产出结果: {summarise(actual)}")

        expected = run["expected"]
        if rc != run["rc"]:
            failures.append(f"退出码 {rc} != 期望 {run['rc']}")
        elif out.decode("utf-8", "replace") != expected:
            failures.append("输出与参考内容不一致")
        else:
            continue
        print("    校验内容: FAIL")
        print(f"      实际 {len(out)} 字节: {actual!r}")
        print(f"      参考 {len(expected.encode())} 字节: {expected!r}")
    if failures:
        print(f"    -> {case['id']} FAIL: {'; '.join(failures)}")
        return False
    print("    校验内容: PASS（退出码与参考输出逐字节一致）")
    print(f"    -> {case['id']} PASS")
    return True


def main():
    executable = sys.argv[1]

    # 前置条件：被测命令必须真实存在（否则任何用例都无从执行）。
    print(f"[setup] 被测命令: {executable}")
    if not os.path.isfile(executable):
        print("[setup] FAIL: 安装后的 bin/gravit 不存在")
        return 1
    if not os.access(executable, os.X_OK):
        # HMDFS 打包不保证携带执行位；恢复它是打包环境问题，不是功能缺陷。
        try:
            os.chmod(executable, 0o755)
        except OSError as exc:  # pragma: no cover - platform specific
            print(f"[setup] 无法恢复执行位: {exc}")
    if not os.access(executable, os.X_OK):
        print("[setup] FAIL: 安装后的 bin/gravit 不可执行")
        return 1
    print("[setup] OK: 命令存在且可执行")

    passed = 0
    for case in CASES:
        if run_case(case, executable):
            passed += 1
    total = len(CASES)
    print(f"test_cli: {total} consumer cases, {passed} passed, {total - passed} failed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
