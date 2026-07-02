#!/usr/bin/env bash
# sign-so.sh — Sign one or more bare .so files for HarmonyOS-PC using DevEco's
# binary-sign-tool.jar (self-sign mode, sufficient for development / on-device testing).
#
# HMOS-PC enforces code-signing on every shared library loaded via
# dlns_add_plugin_default_ld_dictionary. Unsigned .so files can be dlopen'd
# without error, but dlsym returns NULL for all symbols — a silent failure
# that looks like "0/N symbols found" rather than a clear signing error.
#
# This script signs .so files IN PLACE (overwrites the original).
#
# 签名器（三选一，参数一致）：
#   1) 鸿蒙 PC：原生 binary-sign-tool（不需要 java）——放进 PATH，或 SIGN_TOOL=<可执行路径>
#   2) mac：DevEco 的 java -jar binary-sign-tool.jar（DEVECO/JAVA/JAR 覆盖路径）
#
# Override via env:
#   SIGN_TOOL=/path/to/binary-sign-tool          # 原生工具（优先）
#   DEVECO=/Applications/DevEco-Studio.app        # mac 回退
#   JAVA=$DEVECO/Contents/jbr/Contents/Home/bin/java
#   JAR=$DEVECO/Contents/sdk/default/openharmony/toolchains/lib/binary-sign-tool.jar
#
# Usage:
#   ./sign-so.sh libGLU.so [libfoo.so ...]
#
# After signing, push to device:
#   hdc file send libGLU.so /storage/media/100/local/files/Docs/usr/local/lib/libGLU.so

set -euo pipefail

# 逃生口：SKIP_SIGN 非空时跳过签名（如 mac 仅验证编译/链接、本机无签名器；.so 不在本机运行）。
# 设备原生出包、正式发布切勿设——未签名 .so 在鸿蒙 PC 上 dlopen 后 dlsym 全返回 NULL。
if [ -n "${SKIP_SIGN:-}" ]; then
  echo "  [sign-so] SKIP_SIGN 已设：跳过 .so 签名（仅限不在本机运行的验证场景）" >&2
  exit 0
fi

# 解析签名器为 SIGN 数组：SIGN_TOOL 显式 > PATH 里的原生 binary-sign-tool > mac 的 java -jar jar
if [ -n "${SIGN_TOOL:-}" ] && [ -x "$SIGN_TOOL" ]; then
  SIGN=("$SIGN_TOOL")
elif command -v binary-sign-tool >/dev/null 2>&1; then
  SIGN=(binary-sign-tool)
else
  DEVECO=${DEVECO:-/Applications/DevEco-Studio.app}
  JAVA=${JAVA:-$DEVECO/Contents/jbr/Contents/Home/bin/java}
  JAR=${JAR:-$DEVECO/Contents/sdk/default/openharmony/toolchains/lib/binary-sign-tool.jar}
  if [ -x "$JAVA" ] && [ -f "$JAR" ]; then
    SIGN=("$JAVA" -jar "$JAR")
  else
    echo "ERROR: 找不到签名器。任选其一：" >&2
    echo "  - 设 SIGN_TOOL=<binary-sign-tool 可执行路径>" >&2
    echo "  - 或把原生 binary-sign-tool 放进 PATH（鸿蒙 PC，无需 java）" >&2
    echo "  - 或(mac) 设 DEVECO/JAVA/JAR 指向 DevEco 的 java + binary-sign-tool.jar" >&2
    exit 2
  fi
fi

if [ $# -lt 1 ]; then
  echo "Usage: $0 <file.so> [<file2.so> ...]" >&2
  exit 2
fi

# llvm-objcopy（移除旧 .codesign 用）：OHOS NDK > PATH。
OBJCOPY=""
for _cand in "${OHOS_NDK_HOME:-}/llvm/bin/llvm-objcopy" "${OHOS_NDK_ROOT:-}/llvm/bin/llvm-objcopy"; do
  if [ -n "$_cand" ] && [ -x "$_cand" ]; then OBJCOPY="$_cand"; break; fi
done
if [ -z "$OBJCOPY" ] && command -v llvm-objcopy >/dev/null 2>&1; then OBJCOPY="llvm-objcopy"; fi

sign_one() {
  local so_path=$1
  local tmp_out="${so_path}.signed-tmp"
  # 强制重签（关键）：先移除任何已有 .codesign——尤其设备链接器在链接时自动加的那个。
  # 该链接器自签只在「.so 被 bundle 进 HAP、再经 hvigor 用 app 证书重签」后才有效；
  # 若直接从 ~/usr/local 等外部目录独立 dlopen，XPM 会判 Permission denied。故这里一律
  # 剥掉旧签名、再用 binary-sign-tool 显式自签，得到可独立加载的有效自签。
  if [ -n "$OBJCOPY" ]; then
    if "$OBJCOPY" --remove-section .codesign "$so_path" "${so_path}.nocs" 2>/dev/null; then
      mv "${so_path}.nocs" "$so_path"
    else
      rm -f "${so_path}.nocs"
    fi
  fi
  # 官方 CLI（二进制签名工具文档）：自签名 = sign -inFile -outFile -selfSign 1，无 -mode。
  # 原生 binary-sign-tool 严格校验会拒 -mode（mac 的 java jar 容忍，故未暴露）。
  "${SIGN[@]}" sign \
      -inFile  "$so_path" \
      -outFile "$tmp_out" \
      -selfSign 1 >/dev/null
  mv "$tmp_out" "$so_path"
}

total=0; signed=0; already=0; skipped=0

for so_path in "$@"; do
  if [ ! -f "$so_path" ]; then
    echo "SKIP (not a file): $so_path" >&2
    skipped=$((skipped + 1))
    continue
  fi

  name=$(basename "$so_path")
  total=$((total + 1))

  # 一律重签：无法从 display-sign 区分「链接器自签(独立加载无效)」与「binary-sign-tool 自签(有效)」，
  # 两者都显示 self-sign；故不再跳过 already-signed，统一剥旧签名 + 重签，保证可独立 dlopen。
  echo "  signing:        $name"
  sign_one "$so_path"
  signed=$((signed + 1))
done

echo
echo "Done. $total .so total, $signed newly signed, $already already signed, $skipped skipped."
