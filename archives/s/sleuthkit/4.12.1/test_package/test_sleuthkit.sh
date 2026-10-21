#!/bin/sh
# test_package 消费者测试 — sleuthkit 4.12.1(工具类,全部离线)
# TSK_BIN=已安装工具的 bin 目录,由 conanfile.py 传入。
# 断言共 12 项;任一失败即非零退出,conan test 会捕获。

# set -u(审阅 P2-1 说明):消费者测试所有变量必须显式初始化;未定义
# 变量静默展开为空串会让 TSK_BIN 缺失等环境错误被误判为"测试通过"。
set -u

TSK_BIN="${TSK_BIN:?TSK_BIN not set}"
WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT
FAILED=0

check() {
    # check <描述> <期望子串> <命令...>
    desc="$1"; shift
    expect="$1"; shift
    out="$("$@" 2>&1)"
    rc=$?
    if [ "$rc" -ne 0 ]; then
        echo "FAIL: $desc (rc=$rc)"; echo "$out" | sed 's/^/    /'
        FAILED=$((FAILED + 1))
        return
    fi
    case "$out" in
    *"$expect"*) echo "OK: $desc" ;;
    *) echo "FAIL: $desc (输出缺少期望内容 '$expect')"
       echo "$out" | sed 's/^/    /'
       FAILED=$((FAILED + 1)) ;;
    esac
}

check_rc0() {
    # check_rc0 <描述> <命令...>(只断言退出码 0 与非空输出)
    desc="$1"; shift
    out="$("$@" 2>&1)"
    rc=$?
    if [ "$rc" -ne 0 ]; then
        echo "FAIL: $desc (rc=$rc)"; echo "$out" | sed 's/^/    /'
        FAILED=$((FAILED + 1))
        return
    fi
    if [ -z "$out" ]; then
        echo "FAIL: $desc (输出为空)"
        FAILED=$((FAILED + 1))
        return
    fi
    echo "OK: $desc"
}

# ---- 1-10: 核心工具 -V 版本输出(真实执行) ----
check "fls -V 版本"        "4.12.1" "$TSK_BIN/fls" -V
check "icat -V 版本"       "4.12.1" "$TSK_BIN/icat" -V
check "mmls -V 版本"       "4.12.1" "$TSK_BIN/mmls" -V
check "fsstat -V 版本"     "4.12.1" "$TSK_BIN/fsstat" -V
check "img_stat -V 版本"   "4.12.1" "$TSK_BIN/img_stat" -V
check "blkls -V 版本"      "4.12.1" "$TSK_BIN/blkls" -V
check "istat -V 版本"      "4.12.1" "$TSK_BIN/istat" -V
check "jls -V 版本"        "4.12.1" "$TSK_BIN/jls" -V
check "pstat -V 版本"      "4.12.1" "$TSK_BIN/pstat" -V
check "tsk_recover -V 版本" "4.12.1" "$TSK_BIN/tsk_recover" -V

# ---- 11: libtsk 镜像层真实操作:自生成 1MiB raw 镜像,img_stat 打开 ----
RAW="$WORKDIR/test.img"
dd if=/dev/zero of="$RAW" bs=1048576 count=1 2>/dev/null
printf 'OHOS_TSK_MARKER_2026' | dd of="$RAW" bs=1 seek=4096 conv=notrunc 2>/dev/null
check_rc0 "img_stat 真实打开 raw 镜像" "$TSK_BIN/img_stat" "$RAW"

# ---- 12: libtsk 内容检索:srch_strings 在 raw 镜像中找回预埋标记 ----
check "srch_strings 检索预埋标记" "OHOS_TSK_MARKER_2026" "$TSK_BIN/srch_strings" "$RAW"

if [ "$FAILED" -ne 0 ]; then
    echo "FAILED assertions: $FAILED"
    exit 1
fi
echo "all 12 consumer assertions passed"
