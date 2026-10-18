#!/bin/sh
# ukopp 4.9 consumer test — real binary invocations with assertions.
#
# Usage: test_ukopp.sh <ukopp-binary>
#
# Execution model (set by test_package/conanfile.py from the ELF header):
#   native   — the binary matches the test host (CI HarmonyOS PC worker):
#              exec it directly.
#   emulated — foreign-architecture host (x86_64 Linux dev box cross-building
#              for OHOS aarch64): UKOPP_RUNNER=qemu-aarch64, exec'd against
#              the OHOS guest sysroot (UKOPP_GUEST_ROOT) with the guest-side
#              shim stack (UKOPP_GUEST_PRELOAD, colon-separated) preloaded in
#              the guest via -E (so the host loader never sees the aarch64
#              shims): libchkfcnshim/libpcmchkshim/libarc4shim/
#              libmemchrchkshim provide the OHOS fortify (__*_chk),
#              arc4random and backtrace symbols that the stock-musl guest
#              libc lacks; libc++_shared.so is loaded normally from the
#              guest sysroot (ukopp + harfbuzz DT_NEEDED it).
#              Precedent: archives/m/musicpc/0.35, archives/t/tasksh/1.2.0,
#              archives/a/array-hash/0.7.2, archives/v/vimpc/0.09.2.
#
# 覆盖：
#   A1 打包二进制存在且可执行
#   A2 ELF64 / AArch64（e_machine=0xb7）
#   A3 DT_NEEDED 闭包含 GTK3 栈（libgtk-3.so.0/libgdk-3.so.0/libglib-2.0.so.0，
#      无 readelf 时跳过）
#   A4 功能运行：ukopp -nogui（全新 $HOME）→ rc=0。zfuncs zinitapp() 在
#      stdin 非 tty 时把 stdout/stderr 重定向到 $HOME/.ukopp/logfile →
#      断言读 logfile：启动横幅 "========== start ukopp" + 版本/许可报告
#      （"ukopp v.4.9" + "free software: ..."；root 下游打印 "you have
#      root privileges"，同样视为通过——initfunc 按 getuid() 分支）。
#      -nogui 不调 gtk_init()（main() 先判 Fgui 再进 GTK 路径），
#      headless 安全；无 job 文件时不执行备份，直接干净退出。
set -u

UKOPP="$1"
pass=0
fail=0

ok() { pass=$((pass+1)); echo "ok - $1"; }
no() { fail=$((fail+1)); echo "NOT OK - $1"; }

# Command prefix for the emulated model. No quoting inside CMD_PREFIX on
# purpose: the paths are space-free by construction and the prefix is meant
# to word-split (POSIX sh has no arrays).
CMD_PREFIX=""
if [ -n "${UKOPP_RUNNER:-}" ]; then
    CMD_PREFIX="$UKOPP_RUNNER -L $UKOPP_GUEST_ROOT"
    if [ -n "${UKOPP_GUEST_PRELOAD:-}" ]; then
        CMD_PREFIX="$CMD_PREFIX -E LD_PRELOAD=$UKOPP_GUEST_PRELOAD"
    fi
fi

echo "# ukopp 4.9 consumer test"
echo "# ukopp: $UKOPP"
if [ -n "${UKOPP_RUNNER:-}" ]; then
  echo "# emulated via: $CMD_PREFIX"
fi

# --- A1: 打包二进制存在且可执行 --------------------------------------------
if [ -f "$UKOPP" ] && [ -x "$UKOPP" ]; then
  ok "A1 packaged binary exists and is executable"
else
  no "A1 packaged binary missing or not executable: $UKOPP"
fi

# --- A2: ELF64 / AArch64 ----------------------------------------------------
MAGIC="$(od -An -tx1 -N4 "$UKOPP" | tr -d ' \n')"
CLASS="$(od -An -tx1 -j4 -N1 "$UKOPP" | tr -d ' \n')"
EM="$(od -An -tx1 -j18 -N2 "$UKOPP" | tr -d ' \n')"
if [ "$MAGIC" = "7f454c46" ] && [ "$CLASS" = "02" ] && [ "$EM" = "b700" ]; then
  ok "A2 ELF64 AArch64 (e_machine=0xb7)"
else
  no "A2 not ELF64/AArch64: magic=$MAGIC class=$CLASS e_machine=$EM"
fi

# --- A3: DT_NEEDED 闭包含 GTK3 栈 ------------------------------------------
READELF="$(command -v llvm-readelf || command -v readelf || true)"
if [ -n "$READELF" ]; then
  NEED="$($READELF -d "$UKOPP" 2>/dev/null || true)"
  a3=ok
  for lib in libgtk-3.so.0 libgdk-3.so.0 libglib-2.0.so.0; do
    if ! echo "$NEED" | grep -q "$lib"; then
      a3="missing DT_NEEDED: $lib"
    fi
  done
  if [ "$a3" = "ok" ]; then
    ok "A3 DT_NEEDED closure carries the GTK3 stack ($(echo "$NEED" | grep -c '(NEEDED)') NEEDED entries)"
  else
    no "A3 $a3"
  fi
else
  echo "# A3 SKIP (no readelf in environment)"
fi

# --- A4: 功能运行 ukopp -nogui → rc=0 + logfile 断言 -----------------------
# 全新 $HOME（zinitapp 会 mkdir $HOME/.ukopp 并在 stdin 非 tty 时把
# stdout/stderr freopen 到 $HOME/.ukopp/logfile）。< /dev/null 保证非 tty。
TESTROOT=$(mktemp -d "${TMPDIR:-/tmp}/ukopp-test.XXXXXX")
trap 'rm -rf "$TESTROOT"' EXIT
TESTHOME="$TESTROOT/home"
mkdir -p "$TESTHOME"
LOG="$TESTHOME/.ukopp/logfile"

out=$(HOME="$TESTHOME" timeout 20 $CMD_PREFIX "$UKOPP" -nogui </dev/null 2>&1)
rc=$?

if [ "$rc" -ne 0 ]; then
  no "A4 ukopp -nogui exits rc=$rc (expected 0)"
  echo "  output: $out"
  if [ -f "$LOG" ]; then
    echo "  logfile(first 300): $(head -c 300 "$LOG")"
  fi
else
  ok "A4 ukopp -nogui exits rc=0"
  if [ -f "$LOG" ]; then
    ok "A5 \$HOME/.ukopp/logfile produced by zinitapp redirect"
    if grep -q "========== start ukopp" "$LOG"; then
      ok "A6 startup banner present in logfile"
    else
      no "A6 no startup banner in logfile"
      echo "  logfile(first 300): $(head -c 300 "$LOG")"
    fi
    # initfunc 按 getuid() 分支：非 root 打印版本+许可（Help/about 路径），
    # root 打印 "you have root privileges"——两者都证明真实运行到 initfunc
    if grep -q "ukopp v.4.9" "$LOG"; then
      ok "A7 version banner (ukopp v.4.9) reported"
    elif grep -q "root privileges" "$LOG"; then
      ok "A7 root-privileges notice reported (getuid()==0 branch)"
    else
      no "A7 neither version banner nor root notice in logfile"
      echo "  logfile(first 300): $(head -c 300 "$LOG")"
    fi
  else
    no "A5 no \$HOME/.ukopp/logfile produced (zinitapp redirect missing)"
    echo "  output: $out"
  fi
fi

echo "1..$((pass+fail))"
echo "# passed: $pass"
echo "# failed: $fail"
[ "$fail" -eq 0 ] || exit 1
exit 0
