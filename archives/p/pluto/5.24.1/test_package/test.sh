#!/bin/sh
# pluto L1 smoke test — substantively exercise the tested package (R34) by
# running the pluto daemon binary and asserting the capability banner. This
# confirms the NSS crypto backend and the XFRM kernel interface are compiled
# in (a link-only / empty-shell test would not).
#
# pluto is located via PATH (the conanrun env prepends the pluto package
# bindir) and its NSS/NSPR/libevent shared-library runtime dependencies resolve
# via LD_LIBRARY_PATH (the same conanrun env, see the recipe's package_info
# runenv fix for the static-registered nss).
set -e
out=$(pluto --version 2>&1) || {
    echo "FAIL: pluto --version exited non-zero: $out"
    exit 1
}
case "$out" in
    *Libreswan*)
        echo "PASS: pluto --version -> $out"
        ;;
    *)
        echo "FAIL: pluto --version did not report the Libreswan banner: $out"
        exit 1
        ;;
esac

# 上游自测入口（rule4 执行率修复——CI 内真实执行上游测试代码，非仅横幅断言）：
# 3 个零参数自测 check 工具（上游 testing/programs，上游未配 local-check
# harness，直接运行即自测，含 leak detective 泄漏检查）+ algparse 两种模式：
#   --tp = proposal 字符串解析（上游 algparse 的 local-check 入口）
#   --ta = test_ike_alg 官方向量自测（AES-CBC/CTR/GCM + HMAC-SHA1 KDF），
#         向量失败走 pasassert 致命断言（进程非零退出），exit=0 即全过。
for t in _enumcheck _hunkcheck _keyidcheck; do
    out=$("$t" 2>&1) || {
        echo "FAIL: $t exited non-zero: $out"
        exit 1
    }
    echo "PASS: $t"
done
out=$(algparse --tp 2>&1) || {
    echo "FAIL: algparse --tp exited non-zero: $out"
    exit 1
}
echo "PASS: algparse --tp (upstream proposal parsing self-test)"
out=$(algparse --ta 2>&1) || {
    echo "FAIL: algparse --ta exited non-zero: $out"
    exit 1
}
echo "PASS: algparse --ta (upstream test_ike_alg crypto-vector self-test)"

# 鸿蒙特有消费者用例（rule12）— 在 HongMeng 内核上真实跑通 pluto 消费者
# 流程（加载含 conn 的真实 ipsec.conf + 能力横幅 + 平台限制实证），非纯断言。
sh "$(dirname "$0")/harmony_consumer_test.sh"
