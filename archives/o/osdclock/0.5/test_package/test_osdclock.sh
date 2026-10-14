#!/bin/sh
# osdclock 0.5 test_package —— 真实执行被测二进制（R34 / R51）。
#
# 用例设计（全部无需 X server 与输入文件；对真机显示状态零副作用）：
# 1. -h            : getopt 解析后立即打印 usage 并 return EXIT_SUCCESS
#                    （osd_clock.c 第 96-107 行），早于 xosd_init()，不触碰 X。
# 2. --help        : 同一路径的长选项形态（getopt_long）。
# 3. -c red        : 无可达 display 时 xosd_init() → XOpenDisplay() 失败 →
#                    xosd_init() 返回 NULL → osd_clock 打印
#                    "Error initializing osd" 并 return EXIT_FAILURE
#                    （osd_clock.c 第 112-117 行；libxosd 2.2.14
#                    src/libxosd/xosd.c:715-719 "Cannot open display"）。
#                    该用例同时是 patches/0002 的回归探针：若 getopt_long()
#                    返回值仍用无符号 `char` 承接（aarch64 默认），
#                    (c = getopt_long(...)) != -1 恒真 → 程序在 xosd_init()
#                    之前空转挂死；timeout 兜底判 FAIL（改前实测挂死）。
# 4. 选项组合       : -f/-o/-t/-d 组合同样走到初始化失败路径，证明这些选项被
#                    正常解析（不是提前退出）。
# 5. readelf -d    : NEEDED 中含 libxosd.so.2，证明链接的是被测包本体。
#
# 安全模式说明：本脚本由 runner 以 POSIX sh（/bin/sh）解释执行，故用
# `set -eu` 而非 code-style §7 的 `set -euo pipefail`（pipefail 非 POSIX，
# dash 会直接报 Illegal option）；所有断言均不依赖管道退出状态——
# readelf 输出先落到变量再在 shell 内匹配，不使用管道短路。
#
# 退出码：全部断言通过 0，否则 1；末行打印机器可读汇总。
set -eu

BIN="${1:?usage: test_osdclock.sh <path-to-osd_clock> [real-lib-dir]}"
REAL_LIBS="${2:-}"
# HMDFS: 依赖包的 libX.so/libX.so.N 是读不到的 symlink，运行时 loader
# 需要实体文件；test_package generate() 已把实体 .so 复制到 realdep_libs。
if [ -n "$REAL_LIBS" ] && [ -d "$REAL_LIBS" ]; then
  LD_LIBRARY_PATH="${REAL_LIBS}${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
  export LD_LIBRARY_PATH
  echo "  ----  LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
fi

TOTAL=0
PASSED=0
FAILED=0
SKIPPED=0

ok()  { TOTAL=$((TOTAL + 1)); PASSED=$((PASSED + 1)); printf '  PASS  %s\n' "$1"; }
bad() { TOTAL=$((TOTAL + 1)); FAILED=$((FAILED + 1)); printf '  FAIL  %s\n' "$1"; }
skip(){ SKIPPED=$((SKIPPED + 1)); printf '  SKIP  %s\n' "$1"; }

assert_eq() { # assert_eq <desc> <want> <got>
  if [ "$2" = "$3" ]; then ok "$1 (=$2)"; else bad "$1 (want '$2', got '$3')"; fi
}

assert_has() { # assert_has <desc> <needle> <haystack>
  case "$3" in
    *"$2"*) ok "$1" ;;
    *) bad "$1 (missing '$2' in: $3)" ;;
  esac
}

# 无 display：确保走 libxosd 的初始化失败分支，也保证不会真的去连 X server。
unset DISPLAY

# 有界执行：无 timeout 时退化为直接执行（本机/CI 均有 toybox timeout）。
TIMEOUT=""
for c in timeout /system/bin/timeout /usr/bin/timeout /bin/timeout; do
  if command -v "$c" >/dev/null 2>&1; then TIMEOUT="$c"; break; fi
done

run_case() { # run_case <desc> <expected_rc> [args...]
  desc="$1"; want="$2"; shift 2
  RC=0
  if [ -n "$TIMEOUT" ]; then
    OUT=$("$TIMEOUT" 60 "$BIN" "$@" 2>&1) || RC=$?
  else
    OUT=$("$BIN" "$@" 2>&1) || RC=$?
  fi
  printf '  ----  %s -> rc=%s\n' "$desc" "$RC"
  assert_eq "$desc: exit code" "$want" "$RC"
}

echo "== osdclock 0.5 test_package: $BIN"

run_case "-h" 0 -h
assert_has "-h prints usage banner" "USAGE:" "$OUT"

run_case "--help" 0 --help
assert_has "--help prints usage banner" "USAGE:" "$OUT"

run_case "-c red (no X display)" 1 -c red
assert_has "-c red reports init failure" "Error initializing osd" "$OUT"

run_case "-f fixed -o 5 -t -d 2 (no X display)" 1 -f fixed -o 5 -t -d 2
assert_has "option combination reaches init failure" \
  "Error initializing osd" "$OUT"

READELF=""
for c in /data/service/hnp/bin/readelf /usr/bin/readelf /system/bin/readelf; do
  if [ -x "$c" ]; then READELF="$c"; break; fi
done
if [ -n "$READELF" ]; then
  # 不依赖 pipefail：readelf 输出先取到变量，再在 shell 内匹配。
  READELF_OUT=$("$READELF" -d "$BIN" 2>/dev/null || true)
  case "$READELF_OUT" in
    *libxosd.so.2*) ok "DT_NEEDED links libxosd (=libxosd.so.2)" ;;
    *) bad "DT_NEEDED is missing libxosd.so.2" ;;
  esac
else
  skip "readelf unavailable; DT_NEEDED check skipped (assertion not counted)"
fi

printf 'HMBS_TEST_PACKAGE_RESULT={"total":%s,"passed":%s,"failed":%s,"skipped":%s}\n' \
  "$TOTAL" "$PASSED" "$FAILED" "$SKIPPED"
[ "$FAILED" -eq 0 ] || exit 1
exit 0
