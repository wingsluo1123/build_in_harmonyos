#!/bin/sh
# 消费者测试 —— 真实运行 autofdo 提供的 7 个 CLI 二进制，断言其 gflags 行为。
#
# 断言依据（上游 bundled gflags：gflags/gflags_reporting.cc
# HandleCommandLineHelpFlags()/DescribeOneFlag()，本包 7 个 CLI 全部调用
# google::ParseCommandLineFlags）：
#   * `--help`    把全部 flag + 程序名打印到 stdout，随后 exit(1)
#                 （gflags 文档化行为：help 用 exit(1) 表示"非错误但非成功"）；
#                 gflags 帮助里 flag 以**单破折号**列出（`    -flag (描述)`，
#                 例如 `    -binary (Binary file name)`；命令行仍接受 `--flag`）。
#   * `--version` 把 ProgramInvocationShortName（= 工具程序名）打印到 stdout，
#                 随后 exit(0)（gflags 显式注释 "Unlike help ... return 0"）。
#
# 每个工具因此做两种真实调用，并断言【精确退出码】+【输出内容】：
#   --help    : exit == 1 且输出包含该工具**自身**的 gflags flag
#               （如 `-binary`/`-input`/`-output_file`/`-compare_function`），
#               证明列出的是这个二进制的 flag 表；dump_gcov 无自定义 flag，
#               断言输出含其程序名。
#   --version : exit == 0 且输出包含该工具程序名。
# 非空壳：逐工具 exec 被测二进制并解析其 gflags 命令行。
set -u

fail=0

# check_help <tool> <needle>
check_help() {
    tool="$1"; needle="$2"
    out=$("$tool" --help 2>&1); st=$?
    if [ "$st" -ne 1 ]; then
        echo "FAIL: $tool --help exit=$st (gflags --help 期望 exit=1)"
        printf '%s\n' "$out" | head -5
        fail=1
        return
    fi
    if [ -z "$out" ]; then
        echo "FAIL: $tool --help 无输出"
        fail=1
        return
    fi
    if ! printf '%s' "$out" | grep -q -- "$needle"; then
        echo "FAIL: $tool --help 输出缺少 '$needle'"
        printf '%s\n' "$out" | head -15
        fail=1
        return
    fi
    echo "ok: $tool --help exit=1 且输出含 '$needle'"
}

# check_version <tool>
check_version() {
    tool="$1"
    out=$("$tool" --version 2>&1); st=$?
    if [ "$st" -ne 0 ]; then
        echo "FAIL: $tool --version exit=$st (gflags --version 期望 exit=0)"
        printf '%s\n' "$out" | head -5
        fail=1
        return
    fi
    if ! printf '%s' "$out" | grep -q -- "$tool"; then
        echo "FAIL: $tool --version 输出缺少工具名 '$tool'"
        printf '%s\n' "$out" | head -5
        fail=1
        return
    fi
    echo "ok: $tool --version exit=0 且输出含 '$tool'"
}

# --help：断言输出含该工具自身的 gflags flag（gflags 以单破折号列出）。
check_help create_gcov       -binary
check_help sample_merger     -binary
check_help profile_update    -input
check_help create_llvm_prof  -binary
check_help profile_merger    -output_file
check_help profile_diff      -compare_function
# dump_gcov 无自定义 flag（仅 gflags/gcov 内建）；断言 --help 输出含其程序名。
check_help dump_gcov         dump_gcov

# --version：断言 exit=0 且打印工具程序名。
check_version create_gcov
check_version sample_merger
check_version profile_update
check_version create_llvm_prof
check_version dump_gcov
check_version profile_merger
check_version profile_diff

exit $fail
