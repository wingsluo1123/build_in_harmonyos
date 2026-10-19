#!/data/service/hnp/bin/bash
# test_xdrawchem.sh — xdrawchem 1.11.1 test_package 驱动（R34：实质执行被测包二进制）
#
# 用法: bash test_xdrawchem.sh <bin_dir> <data_dir> [work_dir]
#   data_dir = <package>/share/xdrawchem（上游 RINGHOME）
#   work_dir 缺省回退 ${TMPDIR:-/tmp}/xdrawchem-test-$$，不污染配方目录
#
# 断言:
#   TC-01 xdrawchem --version 输出 "XDrawChem"
#   TC-02 xdrawchem --help 输出 "Usage:" 与 "xdrawchem"
#   TC-03 【鸿蒙特有】可执行文件为 OHOS aarch64 ELF（e_machine=0xB7）且可在本机执行
#   TC-04 链接产物含 Qt5Widgets 与 openbabel（DT_NEEDED 字符串存在，非空壳包）
#   TC-05 上游运行期数据随包安装：share/xdrawchem/xdrawchemrc + doc/index.html
set -euo pipefail

BIN_DIR="${1:-}"
DATA_DIR="${2:-}"
WORK="${3:-${TMPDIR:-/tmp}/xdrawchem-test-$$}"
XDRAW="$BIN_DIR/xdrawchem"

if [ -z "$BIN_DIR" ] || [ ! -x "$XDRAW" ]; then
    echo "FAIL: xdrawchem binary not executable: $XDRAW"
    exit 1
fi

PASS=0
FAIL=0
TOTAL=0

check() {
    TOTAL=$((TOTAL + 1))
    if [ "$1" = "1" ]; then
        PASS=$((PASS + 1))
        echo "  PASS  $2"
    else
        FAIL=$((FAIL + 1))
        echo "  FAIL  $2"
    fi
}

echo "=== xdrawchem 1.11.1 test_package ==="
echo "bin_dir=$BIN_DIR"
echo "data_dir=$DATA_DIR"

rm -rf "$WORK"
mkdir -p "$WORK"
cd "$WORK"

# TC-01 --version（打印版本后 exit 0，不需要显示设备）
# `|| true`：需要捕获输出并按内容判定，非 0 退出码不参与本断言（set -e 下防中断）
OUT="$("$XDRAW" --version 2>&1 || true)"
case "$OUT" in
    *XDrawChem*) check 1 "TC-01-version" ;;
    *) echo "    got: $OUT"; check 0 "TC-01-version" ;;
esac

# TC-02 --help（usage() 以 exit 0 结束）
# `|| true`：同上，退出码不参与断言，只看输出内容
OUT="$("$XDRAW" --help 2>&1 || true)"
case "$OUT" in
    *"Usage:"*xdrawchem*) check 1 "TC-02-help" ;;
    *) echo "    got: $OUT"; check 0 "TC-02-help" ;;
esac

# TC-03 【鸿蒙特有】OHOS aarch64 ELF（e_machine = 0xB7，小端字节序 b7 00）
# `|| true`：od/tr 不可用或读取失败时按"非 aarch64"判定，不因 pipefail 直接中断
MACHINE="$(od -An -tx1 -j18 -N2 "$XDRAW" 2>/dev/null | tr -d ' \n' || true)"
case "$MACHINE" in
    b700)
        if "$XDRAW" --version >/dev/null 2>&1; then
            check 1 "TC-03-ohos-aarch64-elf-runs-on-device"
        else
            check 0 "TC-03-ohos-aarch64-elf-runs-on-device"
        fi
        ;;
    *)
        echo "    got e_machine=$MACHINE (expect b700)"
        check 0 "TC-03-ohos-aarch64-elf-runs-on-device"
        ;;
esac

# TC-04 链接了 Qt5Widgets / openbabel（防止把空壳或错链二进制打进包）
# ⚠️ 不能用 grep：conan 注入的运行环境 PATH 中 /system/bin 先于 /data/service/hnp/bin，
#    命中的是 **toybox grep 0.8.12**，它对二进制文件默认跳过（-a 亦无效），恒不命中。
#    改用 `tr -d '\000'` 去 NUL 后由 bash 内建 case 做子串匹配（只依赖 toybox tr）。
BIN_TEXT="$(tr -d '\000' < "$XDRAW")"
HAS_QT5=no
HAS_OB=no
case "$BIN_TEXT" in *libQt5Widgets.so.5*) HAS_QT5=yes ;; esac
case "$BIN_TEXT" in *libopenbabel.so.8*) HAS_OB=yes ;; esac
if [ "$HAS_QT5" = "yes" ] && [ "$HAS_OB" = "yes" ]; then
    check 1 "TC-04-links-qt5widgets-and-openbabel"
else
    echo "    DT_NEEDED probe: libQt5Widgets=$HAS_QT5 libopenbabel=$HAS_OB"
    check 0 "TC-04-links-qt5widgets-and-openbabel"
fi

# TC-05 上游运行期数据（RINGHOME = share/xdrawchem；
#       ringdir.path=share/xdrawchem 故 ring/* 平铺于此，doc/* 落在 doc/ 下）
if [ -f "$DATA_DIR/xdrawchemrc" ] && [ -f "$DATA_DIR/doc/index.html" ]; then
    check 1 "TC-05-runtime-data-installed"
else
    echo "    missing: $DATA_DIR/xdrawchemrc or $DATA_DIR/doc/index.html"
    check 0 "TC-05-runtime-data-installed"
fi

echo "--------------------------------------------------------------"
echo "CASE SUMMARY: total=$TOTAL passed=$PASS failed=$FAIL skipped=0"
if [ "$FAIL" -ne 0 ]; then
    echo "RESULT: FAIL"
    exit 1
fi
echo "RESULT: PASS"
exit 0
