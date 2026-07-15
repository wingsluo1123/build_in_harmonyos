#!/bin/bash
# patch-ohos.sh — 为 config.guess/config.sub 打 HarmonyOS 补丁 (E007)
# 用法: bash patch-ohos.sh <source_dir>
set -euo pipefail

SRC_DIR="${1:-.}"

# Patch config.guess
find "$SRC_DIR" -name "config.guess" 2>/dev/null | while read -r f; do
    echo "  [patch] config.guess: $f"
    # 1. Add __OHOS__ LIBC detection after __ANDROID__
    if ! grep -q "__OHOS__" "$f" 2>/dev/null; then
        sed -i '' '/defined(__ANDROID__)/a\
#elif defined(__OHOS__)\
    LIBC=ohos
' "$f" 2>/dev/null || sed -i '/defined(__ANDROID__)/a #elif defined(__OHOS__)\n    LIBC=ohos' "$f" 2>/dev/null || true
    fi
    # 2. Add HarmonyOS system identification before NetBSD
    if ! grep -q "HarmonyOS" "$f" 2>/dev/null; then
        sed -i '' 's/^\([[:space:]]*\*:NetBSD:\*:\*:\))/    *:HarmonyOS:*:*)\
\tcase $UNAME_MACHINE in\
\t    aarch64|arm64) MACHINE=aarch64 ;;\
\t    armv7*|armv8*) MACHINE=arm ;;\
\t    x86_64|amd64)  MACHINE=x86_64 ;;\
\t    i?86)         MACHINE=i686 ;;\
\t    *)            MACHINE="$UNAME_MACHINE" ;;\
\tesac\
\tGUESS=${MACHINE}-unknown-linux-ohos\
\t;;\
\
\1/' "$f" 2>/dev/null || sed -i 's/^\([[:space:]]*\*:NetBSD:\*:\*:\))/    *:HarmonyOS:*:*)\n\tcase $UNAME_MACHINE in\n\t    aarch64|arm64) MACHINE=aarch64 ;;\n\t    armv7*|armv8*) MACHINE=arm ;;\n\t    x86_64|amd64)  MACHINE=x86_64 ;;\n\t    i?86)         MACHINE=i686 ;;\n\t    *)            MACHINE="$UNAME_MACHINE" ;;\n\tesac\n\tGUESS=${MACHINE}-unknown-linux-ohos\n\t;;\n\n\1/' "$f" 2>/dev/null || true
    fi
done

# Patch config.sub
find "$SRC_DIR" -name "config.sub" 2>/dev/null | while read -r f; do
    echo "  [patch] config.sub: $f"
    # 1. Add ohos-linux triplet after android-linux
    if ! grep -q "ohos-linux" "$f" 2>/dev/null; then
        sed -i '' '/^[[:space:]]*android-linux)/a\
		ohos-linux)\
			basic_machine=$field1-unknown\
			basic_os=linux-ohos\
			;;
' "$f" 2>/dev/null || sed -i '/^[[:space:]]*android-linux)/a \\t\tohos-linux)\n\t\t\tbasic_machine=$field1-unknown\n\t\t\tbasic_os=linux-ohos\n\t\t\t;;' "$f" 2>/dev/null || true
    fi
    # 2. Add ohos* to OS list
    if ! grep -q "ohos\*" "$f" 2>/dev/null; then
        sed -i '' 's/\(gnu\*\s*|\s*android\*\)/\1 | ohos*/' "$f" 2>/dev/null || sed -i 's/\(gnu\*\s*|\s*android\*\)/\1 | ohos*/' "$f" 2>/dev/null || true
    fi
    # 3. Add linux-ohos to kernel-OS list
    if ! grep -q "linux-ohos" "$f" 2>/dev/null; then
        sed -i '' 's/\(linux-uclibc\*[\s\/-]*)\)/\1| linux-ohos*)/' "$f" 2>/dev/null || sed -i 's/\(linux-uclibc\*[\s\/-]*)\)/\1| linux-ohos*)/' "$f" 2>/dev/null || true
    fi
done

echo "  [ok] HarmonyOS patches applied"