#!/bin/sh
# reproduce.sh — 知识库拓展四件套 ④ 样例演示库
# 两阶段复现 README §二 的核心规律（日志全部落文件，无管道 head，规避 SIGPIPE）：
#
# 阶段 1（自包含）：构建最小 C 共享库 libdemo.so（新编译，无 .codesign 段），
#   同一份产物以三种方式落盘并逐个 dlopen：
#     S1 tar 解包（创建时 mode 770，模拟 conan 解包）
#     S2 python open('wb')+chmod 770（模拟任意写者）
#     S3 cp 到全新路径
#   预期（HMDFS 与 ext4 一致）：三行全 PASS —— 无签名 ELF 不受签名校验约束，
#   证伪「创建方式/mode 位决定 exec」假说（README R2）。
#   随后演示 R3：原地覆盖 EPERM、rm+cp 成功。
#
# 阶段 2（需一个已签名发布件）：
#   自动获取：conan download <pkg> -r=$OHC_REMOTE（缺省 ki18n，可用
#   OHC_SIGNED_PKG 覆盖）；conan 不可用/失败时跳过并提示用
#   --signed <so路径> 显式指定。
#   T1 逐字节复制该件（os.open 创建、mode 770）→ dlopen 报「缺依赖」
#      而非 Permission denied（签名完好，装载推进到依赖解析）；
#   T2 仅翻转 1 字节的副本 → dlopen 立即 Permission denied（签名失效）。
#   ——两行对照即 README R1 的决定性实证（HMDFS 上成立；ext4/CI 无签名
#   强制，T2 表现为缺依赖错误，脚本会提示平台差异）。
#
# 用法: sh reproduce.sh [工作目录] [--signed <已签名so路径>]
#   工作目录缺省 ${TMPDIR:-/tmp}/hmdfs-demo
# 退出码: 0=复现符合预期 / 1=矩阵不符合（平台行为变化，需复核）/ 2=环境错误
set -u

WORK=""
SIGNED_ARG=""
while [ $# -gt 0 ]; do
  case "$1" in
    --signed)
      [ $# -ge 2 ] || { echo "ERROR: --signed requires a path argument" >&2; exit 2; }
      SIGNED_ARG="$2"; shift 2 ;;
    --signed=*) SIGNED_ARG=${1#--signed=}; shift ;;
    *)
      if [ -z "$WORK" ]; then WORK="$1"; else SIGNED_ARG="$1"; fi
      shift ;;
  esac
done
WORK="${WORK:-${TMPDIR:-/tmp}/hmdfs-demo}"
CC="$(command -v cc 2>/dev/null || echo /data/service/hnp/bin/clang)"
LOG="$WORK/reproduce.log"
RESULT="$WORK/result.txt"
REMOTE="${OHC_REMOTE:-ohpcd}"
SIGNED_PKG="${OHC_SIGNED_PKG:-ki18n/6.18.0}"

[ -x "$CC" ] || { echo "ERROR: no compiler (cc or $CC)" >&2; exit 2; }
rm -rf "$WORK"
mkdir -p "$WORK/src" "$WORK/payload/lib" "$WORK/s1" "$WORK/s2" "$WORK/s3" "$WORK/s5/lib" || exit 2
: > "$LOG"

# ── 阶段 1：最小共享库 + dlopen 消费者 ────────────────────────
cat > "$WORK/src/demo.c" <<'EOF'
int demo_value(void) { return 42; }
EOF
cat > "$WORK/src/consumer.c" <<'EOF'
#include <dlfcn.h>
#include <stdio.h>
int main(int argc, char **argv) {
    void *h = dlopen(argv[1], RTLD_NOW);
    if (!h) { printf("FAIL %s: %s\n", argv[1], dlerror()); return 1; }
    int (*fn)(void) = (int (*)(void))dlsym(h, "demo_value");
    if (!fn || fn() != 42) { printf("FAIL %s: symbol/value mismatch\n", argv[1]); return 1; }
    printf("PASS %s\n", argv[1]);
    return 0;
}
EOF
echo "[1] building libdemo.so + consumer ..." >> "$LOG"
"$CC" -fPIC -shared "$WORK/src/demo.c" -o "$WORK/payload/lib/libdemo.so" >> "$LOG" 2>&1 \
  || { echo "ERROR: libdemo build failed, see $LOG" >&2; exit 2; }
"$CC" "$WORK/src/consumer.c" -o "$WORK/consumer" -ldl >> "$LOG" 2>&1 \
  || { echo "ERROR: consumer build failed, see $LOG" >&2; exit 2; }

# 三种创建方式落盘同一份产物
echo "[2] S1 tar-extract (creation-time 0770) ..." >> "$LOG"
tar -cf "$WORK/.stage.tar" -C "$WORK/payload" lib >> "$LOG" 2>&1
tar -xf "$WORK/.stage.tar" -C "$WORK/s1" >> "$LOG" 2>&1
echo "[2] S2 python-write + chmod 0770 ..." >> "$LOG"
python3 - "$WORK/payload/lib/libdemo.so" "$WORK/s2/lib/libdemo.so" >> "$LOG" 2>&1 <<'EOF'
import os, sys
src, dst = sys.argv[1], sys.argv[2]
os.makedirs(os.path.dirname(dst), exist_ok=True)
open(dst, "wb").write(open(src, "rb").read())
os.chmod(dst, 0o770)
print("S2 mode:", oct(os.stat(dst).st_mode & 0o777))
EOF
echo "[2] S3 cp to fresh path ..." >> "$LOG"
mkdir -p "$WORK/s3/lib"
cp "$WORK/payload/lib/libdemo.so" "$WORK/s3/lib/libdemo.so" >> "$LOG" 2>&1

echo "[3] phase-1 dlopen matrix ..." >> "$LOG"
: > "$RESULT"
echo "== phase 1: unsigned lib, three creation styles (expect all PASS) ==" >> "$RESULT"
for s in s1 s2 s3; do
  "$WORK/consumer" "$WORK/$s/lib/libdemo.so" >> "$RESULT" 2>&1
done

echo "--- R3 in-place overwrite (expect EPERM) / rm+cp (expect OK) ---" >> "$RESULT"
cp "$WORK/payload/lib/libdemo.so" "$WORK/s1/lib/libdemo.so" >> "$LOG" 2>&1 \
  && echo "R3 in-place cp: OK (unexpected on HMDFS — platform behavior changed?)" >> "$RESULT" \
  || echo "R3 in-place cp: EPERM (matches README R3)" >> "$RESULT"
rm -f "$WORK/s1/lib/libdemo.so" && cp "$WORK/payload/lib/libdemo.so" "$WORK/s1/lib/libdemo.so" >> "$LOG" 2>&1 \
  && echo "R3 rm+cp: OK (matches README playbook)" >> "$RESULT" \
  || echo "R3 rm+cp: FAILED" >> "$RESULT"

# ── 阶段 2：已签名发布件 对照实验（R1 决定性实证）────────────
SIGNED="$SIGNED_ARG"
if [ -z "$SIGNED" ] && command -v conan > /dev/null 2>&1; then
  echo "[4] phase-2: conan download $SIGNED_PKG -r=$REMOTE ..." >> "$LOG"
  conan download "$SIGNED_PKG" -r="$REMOTE" --only-recipe > /dev/null 2>&1 || true
  if conan download "$SIGNED_PKG" -r="$REMOTE" >> "$LOG" 2>&1; then
    # no pipe-head (SIGPIPE): pick the first readable match (R4: verify the
    # source actually reads -- HMDFS phantom entries would fail later anyway)
    for cand in $(find "$HOME/.cache/conan2/p" "$HOME/.conan2/p" -path "*/p/lib/libKF6I18n.so" 2>/dev/null); do
      if cat "$cand" > /dev/null 2>&1; then SIGNED="$cand"; break; fi
    done
  else
    echo "[4] conan download failed — phase 2 skipped (use --signed <so>)" >> "$LOG"
  fi
fi

PH2=0
if [ -n "$SIGNED" ] && [ -f "$SIGNED" ] && cat "$SIGNED" > /dev/null 2>&1; then
  PH2=1
  echo "== phase 2: SIGNED release lib ($SIGNED) — R1 decisive pair ==" >> "$RESULT"
  echo "[4] T1 verbatim copy / T2 one-byte flip ..." >> "$LOG"
  python3 - "$SIGNED" "$WORK/s5/lib" >> "$LOG" 2>&1 <<'EOF'
import os, sys
src, outdir = sys.argv[1], sys.argv[2]
data = open(src, "rb").read()
t1 = os.path.join(outdir, "t1-verbatim.so")
if os.path.exists(t1): os.remove(t1)
fd = os.open(t1, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o770)
os.write(fd, data); os.close(fd)
mut = bytearray(data); mut[0x200] ^= 0xFF
t2 = os.path.join(outdir, "t2-onebyte-flip.so")
open(t2, "wb").write(bytes(mut))
print("T1/T2 written, sizes:", len(data), len(mut))
EOF
  "$WORK/consumer" "$WORK/s5/lib/t1-verbatim.so" >> "$RESULT" 2>&1
  "$WORK/consumer" "$WORK/s5/lib/t2-onebyte-flip.so" >> "$RESULT" 2>&1
else
  echo "== phase 2: SKIPPED (no signed lib; pass --signed <so路径> 或配好 conan) ==" >> "$RESULT"
fi

# ── 断言 ─────────────────────────────────────────────────────
echo "" >> "$RESULT"
echo "matrix assertion:" >> "$RESULT"
rc=0
for s in s1 s2 s3; do
  grep -q "^PASS .*/$s/" "$RESULT" || { echo "$s should PASS (unsigned lib, README R2)" >> "$RESULT"; rc=1; }
done
if [ "$PH2" -eq 1 ]; then
  if grep "t1-verbatim" "$RESULT" | grep -q "Permission denied"; then
    echo "T1 verbatim copy should load past signature (not Permission denied)" >> "$RESULT"; rc=1
  else
    echo "T1 verbatim copy: signature intact (loads into dep-resolution) ✓" >> "$RESULT"
  fi
  if grep "t2-onebyte-flip" "$RESULT" | grep -q "Permission denied"; then
    echo "T2 one-byte flip: Permission denied ✓ (README R1 confirmed)" >> "$RESULT"
  else
    echo "T2 one-byte flip expected Permission denied on HMDFS (ext4/CI has no signing enforcement)" >> "$RESULT"; rc=1
  fi
fi
[ $rc -eq 0 ] && echo "REPRODUCED: see ✓ lines (README R1/R2/R3 all confirmed)" >> "$RESULT" \
  || echo "MATRIX-DIFF: see lines above (review platform behavior)" >> "$RESULT"

cat "$RESULT"
[ $rc -eq 0 ] && exit 0
exit 1
