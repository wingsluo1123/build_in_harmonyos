#!/data/service/hnp/bin/bash
# test_rna_star.sh — functional smoke test for the STAR RNA-seq aligner.
# Runs in conanrun env (PATH includes installed bin/).
#
# 消费测试真实驱动打包的 ELF 二进制，共 2 个真实用例：
#   TC1: STAR --version → Parameters::inputParameters 命中 --version 打印
#        STAR_VERSION ("2.7.11b") 并 exit(0)（Parameters.cpp）。
#   TC2: STAR --help → usage() 打印 "STAR version=2.7.11b" 并 exit 0
#        （STAR.cpp usage()）。
#
# HMBS 机器证据标记：discovered/passedCount 来自脚本显式累加的真实用例
# 计数（非对 stdout 做字符串数数）；任一用例失败即打印 passed:false 标记并
# 以非零退出。标记为单行独立 JSON 对象（不包裹在复合对象里）。
set -uo pipefail

TOTAL=2
PASSED=0

fail_test() {
    printf '%s\n' "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"bash test_rna_star.sh\",\"discovered\":${TOTAL},\"passedCount\":${PASSED}}"
    exit 1
}

# --------------------------------------------------------------------------
# TC1: STAR --version — the real binary must print the version and exit 0.
# --------------------------------------------------------------------------
ver="$(STAR --version 2>&1)" || fail_test
if echo "$ver" | grep -q "2.7.11b"; then
    echo "PASS: STAR --version prints 2.7.11b"
    PASSED=$((PASSED + 1))
else
    echo "FAIL: STAR --version unexpected output: $ver"
    fail_test
fi

# --------------------------------------------------------------------------
# TC2: STAR --help — usage() 打印 "STAR version=2.7.11b" 并 exit 0
# --------------------------------------------------------------------------
help_out="$(STAR --help 2>&1)" || fail_test
if echo "$help_out" | grep -q "STAR version=2.7.11b"; then
    echo "PASS: STAR --help prints STAR version=2.7.11b"
    PASSED=$((PASSED + 1))
else
    echo "FAIL: STAR --help missing version banner: $help_out"
    fail_test
fi

echo "ALL TESTS PASSED"
printf '%s\n' "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"command\":\"bash test_rna_star.sh\",\"discovered\":${TOTAL},\"passedCount\":${PASSED}}"
