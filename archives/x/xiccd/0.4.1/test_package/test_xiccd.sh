#!/data/service/hnp/bin/bash
# xiccd 0.4.1 L1 冒烟测试 — 真实执行打包的 bin/xiccd（R34）
#
# PATH 由 test_package 的 VirtualRunEnv(conanrun) 注入，直接按名字调用即可。
# 三个断言全部 headless 可跑（不依赖 X display / colord D-Bus）。
#
# 刻意不使用 `set -e`：断言需要 `out=$("$XICCD" ...); rc=$?` 捕获非零退出码
# （断言 3 正是期待 rc=1），set -e 会在首个非零命令处直接退出，断言随即失去意义。
# `set -u` 保留，用于抓住变量拼写错误。
set -u

XICCD="${XICCD:-xiccd}"
failed=0

echo "== 1) $XICCD -V：show_version() 应在连接 X 之前 exit 0，且带补齐后的版本号"
out=$("$XICCD" -V 2>&1); rc=$?
echo "   rc=$rc  out=$out"
if [ "$rc" -ne 0 ]; then
    echo "   [FAIL] 期望 rc=0，实际 $rc"
    failed=1
fi
case "$out" in
    "xiccd - Version 0.4.1"*)
        echo "   [OK] 版本串正确（0001 补丁固化 AC_INIT 生效）" ;;
    *)
        echo "   [FAIL] 版本串不符，期望以 'xiccd - Version 0.4.1' 开头"
        failed=1 ;;
esac

echo "== 2) $XICCD --help：GLib 应打印 usage 摘要并 exit 0"
out=$("$XICCD" --help 2>&1); rc=$?
echo "   rc=$rc"
if [ "$rc" -ne 0 ]; then
    echo "   [FAIL] 期望 rc=0，实际 $rc"
    failed=1
fi
case "$out" in
    *"X color management daemon"*)
        echo "   [OK] usage 摘要存在" ;;
    *)
        echo "   [FAIL] usage 摘要缺失"
        failed=1 ;;
esac

echo "== 3) $XICCD --nonexistent-flag：未知选项应走错误路径 exit 1（非崩溃）"
out=$("$XICCD" --nonexistent-flag-xyz 2>&1); rc=$?
echo "   rc=$rc  out=$out"
if [ "$rc" -eq 1 ]; then
    echo "   [OK] 按预期 exit 1"
else
    echo "   [FAIL] 期望 exit 1，实际 $rc"
    failed=1
fi

if [ "$failed" -eq 0 ]; then
    echo "ALL CHECKS PASSED"
else
    echo "SOME CHECKS FAILED"
fi
exit "$failed"
