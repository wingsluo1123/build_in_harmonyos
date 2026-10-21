#!/bin/sh
# L1 smoke test for mtd-utils: verify key CLI tools run and report version.
# Called by test_package/conanfile.py test() method (R34: 实质调用被测包二进制)
set -e

SBIN_DIR="$1"
[ -z "$SBIN_DIR" ] && SBIN_DIR="$PWD"

check_tool() {
    tool="$1"
    bin="$SBIN_DIR/$tool"
    if [ ! -x "$bin" ]; then
        echo "FAIL: $tool not found or not executable: $bin"
        exit 1
    fi
    # --version 对多数 mtd-utils 工具可用; 对部分工具(无 --version)用 --help
    OUTPUT=$("$bin" --version 2>&1) || OUTPUT=$("$bin" --help 2>&1)
    if [ -z "$OUTPUT" ]; then
        echo "FAIL: $tool produced no output"
        exit 1
    fi
    echo "PASS: $tool ran: $(echo "$OUTPUT" | head -1)"
}

# mtdinfo 验证版本输出 (mtd-utils 2.3.1)
MTDINFO="$SBIN_DIR/mtdinfo"
if [ ! -x "$MTDINFO" ]; then
    echo "FAIL: mtdinfo not found or not executable: $MTDINFO"
    exit 1
fi
VOUT=$("$MTDINFO" --version 2>&1)
echo "$VOUT" | grep -q "mtd-utils" || { echo "FAIL: mtdinfo --version missing 'mtd-utils': $VOUT"; exit 1; }
echo "$VOUT" | grep -q "2.3.1" || { echo "FAIL: mtdinfo --version missing '2.3.1': $VOUT"; exit 1; }
echo "PASS: mtdinfo --version -> $VOUT"

# 核心工具冒烟: 每个工具至少能运行 (--help 或 --version)
for t in flash_erase nanddump nandwrite mtdinfo flashcp flash_eraseall \
         ubiformat ubinize ubiattach ubiupdatevol ubimkvol ubinfo \
         mkfs.ubifs fsck.ubifs mkfs.jffs2 jffs2dump jffs2reader sumtool; do
    check_tool "$t"
done

echo "PASS: mtd-utils smoke test OK"
exit 0
