#!/system/bin/sh
# test_swift_toolchain.sh -- swift-toolchain-ohos 6.0.3 test_package 驱动器
#
# 为什么是 .sh：test_package 测试源白名单现为 .c/.cpp/.cc/.cxx/.sh/.py
# （scripts/ohc/preflight.py:431；ci/conan/build_and_test.sh:345-358），暂不含 .swift。
# 故用 .sh 外壳，脚本内部**真编译并真运行**一个 Swift 程序。
#
# 断言 11 项（编号与输出里的 [ok N] 一一对应）：
#   S 层静态 5 项：S1 wrapper / S2 交付编译器可执行 / S3 ring 本体与模块 /
#                  S4 sysroot + resource-dir / S5 Swift 运行时闭包 + libc++_shared
#   D 层破坏性反向 2 项：D1 摘掉执行位后 S2 判据必须失败 / D2 恢复后 S2 判据必须再通过
#   E 层运行 3 项：E1 swiftc.sh --version / E2 版本串含 6.0.3 / E3 真编译 Swift 程序
#   R 层运行时自证 1 项：R1 产物在 env -u LD_LIBRARY_PATH 下仍能跑（环 RUNPATH 契约）
#
# ★ D 层是 L1e 口径的破坏性反向验证：**若把被测物破坏掉而检查仍通过，该检查就没有判别力**。
set -u

FAILED=0
N=0
ok()  { N=$((N+1)); echo "[ok $N] $1"; }
bad() { N=$((N+1)); echo "[FAIL $N] $1"; FAILED=$((FAILED+1)); }
chk() { if [ "$2" = "0" ]; then ok "$1"; else bad "$1"; fi; }

# ---------- 定位包根 ----------
ROOT="${SWIFT_TOOLCHAIN_OHOS_ROOT:-}"
if [ -z "$ROOT" ] || [ ! -d "$ROOT" ]; then
  # 回退：从 conanbuild 环境的 PATH 里找 instrument/bin，再上溯包根
  for d in $(printf '%s' "${PATH:-}" | tr ':' ' '); do
    case "$d" in
      */instrument/bin) ROOT=$(cd "$d/../.." && pwd); break ;;
    esac
  done
fi
if [ -z "$ROOT" ] || [ ! -d "$ROOT" ]; then
  echo "[FAIL] cannot locate package root (SWIFT_TOOLCHAIN_OHOS_ROOT unset and PATH has no */instrument/bin)"
  echo "TEST_RESULTS total=11 pass=0 fail=11"
  echo "TEST_VERDICT FAIL"
  exit 1
fi
echo "PKG_ROOT=$ROOT"

WORK="${TMPDIR:-$PWD}/swift-tp-$$"
mkdir -p "$WORK" || { echo "[FAIL] cannot create workdir $WORK"; exit 1; }

# ---------- S 层：静态构成（5 项） ----------
S1=1
if [ -f "$ROOT/env.sh" ] && [ -f "$ROOT/swiftc.sh" ] && [ -f "$ROOT/build-demo.sh" ]; then S1=0; fi
chk "S1 package-root wrappers present (env.sh/swiftc.sh/build-demo.sh)" "$S1"

SWIFTC="$ROOT/instrument/bin/swiftc"
s2_predicate() { [ -f "$1" ] && [ -x "$1" ]; }
S2=1; s2_predicate "$SWIFTC" && S2=0
chk "S2 delivered compiler instrument/bin/swiftc present and executable" "$S2"

S3=1
if [ -f "$ROOT/ring/plane/lib/libFoundation.so" ] && \
   [ -f "$ROOT/ring/plane/modules/Foundation.swiftmodule" ]; then S3=0; fi
chk "S3 ring plane: libFoundation.so + Foundation.swiftmodule" "$S3"

S4=1
if [ -d "$ROOT/sysroot/ohos" ] && [ -d "$ROOT/toolchain/resource/15.0.4" ]; then S4=0; fi
chk "S4 sysroot/ohos + toolchain/resource/15.0.4 present" "$S4"

S5=1
if [ -f "$ROOT/build/swift/lib/swift/ohos/libswiftCore.so" ] && \
   [ -f "$ROOT/toolchain/cxx/libc++_shared.so" ]; then S5=0; fi
chk "S5 Swift runtime closure libswiftCore.so + libc++_shared.so" "$S5"

# ---------- D 层：破坏性反向验证（2 项） ----------
# D1: 摘掉执行位 ⇒ **同一个 S2 判据必须失败**。若仍通过 ⇒ S2 恒真，无判别力。
D1=1
if [ -f "$SWIFTC" ]; then
  chmod a-x "$SWIFTC" 2>/dev/null
  if s2_predicate "$SWIFTC"; then
    # 摘掉执行位后判据仍通过 ⇒ 判据无判别力（或 chmod 未生效）
    echo "     note: chmod a-x had no effect OR predicate is not discriminative"
    D1=1
  else
    D1=0
  fi
  chmod a+x "$SWIFTC" 2>/dev/null
fi
chk "D1 destructive reverse: S2 predicate FAILS with exec bit removed" "$D1"

D2=1
if s2_predicate "$SWIFTC"; then D2=0; fi
chk "D2 exec bit restored: S2 predicate PASSES again" "$D2"

# ---------- E 层：运行（3 项） ----------
E1=1
VERS=$(T2_ENV_QUIET=1 sh "$ROOT/swiftc.sh" --version 2>&1)
VRC=$?
if [ "$VRC" = "0" ] && [ -n "$VERS" ]; then E1=0; fi
chk "E1 swiftc.sh --version exits 0 with output" "$E1"
echo "     version: $(printf '%s' "$VERS" | head -1)"

E2=1
if printf '%s' "$VERS" | grep -q "6\.0\.3"; then E2=0; fi
chk "E2 version string contains 6.0.3" "$E2"

E3=1
cat > "$WORK/hello.swift" <<'SWIFT'
import Foundation
let d = Date(timeIntervalSince1970: 0)
print("swift-toolchain-ohos ok")
print("date-epoch: \(String(describing: d))")
let tz = TimeZone(identifier: "Asia/Shanghai")
print("tz: \(tz?.identifier ?? "nil")")
SWIFT
if T2_ENV_QUIET=1 sh "$ROOT/swiftc.sh" "$WORK/hello.swift" -o "$WORK/hello" >"$WORK/e3.log" 2>&1; then
  if [ -x "$WORK/hello" ]; then E3=0; fi
fi
chk "E3 compile a real Swift program against the ring plane" "$E3"
if [ "$E3" != "0" ]; then
  echo "     --- compile log (tail) ---"
  tail -20 "$WORK/e3.log" 2>/dev/null
fi

# ---------- R 层：运行时自证（1 项） ----------
R1=1
if [ "$E3" = "0" ]; then
  OUT=$(env -u LD_LIBRARY_PATH "$WORK/hello" 2>&1)
  RC=$?
  if [ "$RC" = "0" ]; then
    R1=0
    echo "     run output: $(printf '%s' "$OUT" | head -2 | tr '\n' ' ')"
  else
    echo "     --- run rc=$RC out: $(printf '%s' "$OUT" | head -3) ---"
  fi
fi
chk "R1 built program runs with LD_LIBRARY_PATH unset (ring RUNPATH contract)" "$R1"

# ---------- 汇总 ----------
PASS=$((N-FAILED))
echo "TEST_RESULTS total=$N pass=$PASS fail=$FAILED"
if [ "$FAILED" != "0" ]; then
  echo "TEST_VERDICT FAIL"
  exit 1
fi
echo "TEST_VERDICT PASS"
exit 0
