#!/usr/bin/env bash
# test_package/test.sh — unfurl 0.4.3 消费者功能测试 (五级测试体系 L1)
#
# 用法: bash test.sh [/path/to/unfurl]     (亦可用环境变量 UNFURL_BIN 指定)
#
# 为什么必须逐条断言 stdout 内容:
#   上游 main.go 在 mode 无法识别时, 仅向 stderr 打印 "unknown mode" 后
#   直接 return, 进程退出码依然是 0。也就是说 "命令跑通" 并不能证明
#   "功能正确" —— 只有把实际输出与预期逐条比对, 才是真实测试。
#   (原 test_package 只执行不校验输出, 属于恒真的假阳性测试。)
#
# 预期值来源: 上游 README.mkd 中 urls.txt 的官方示例输入与官方示例输出,
# 不是自行臆造的值。
set -u

UNFURL_BIN="${UNFURL_BIN:-${1:-unfurl}}"
FAILED=0
TOTAL=0

# 上游 README.mkd 的示例 urls.txt
URLS=$(cat <<'EOF'
https://sub.example.com/users?id=123&name=Sam
https://sub.example.com/orgs?org=ExCo#about
http://example.net/about#contact
EOF
)

# 归一化输出: 按字节序排序后用逗号连接。
# 排序是必要的 —— keys/values 源自 Go map (u.Query()), 迭代顺序不确定。
run_mode() {
    printf '%s\n' "$URLS" | "$UNFURL_BIN" "$@" | LC_ALL=C sort | tr '\n' ',' | sed 's/,$//'
}

assert_eq() {
    local name="$1" expected="$2" actual="$3"
    TOTAL=$((TOTAL + 1))
    if [ "$expected" = "$actual" ]; then
        printf 'PASS: %s -> [%s]\n' "$name" "$actual"
    else
        printf 'FAIL: %s\n      expected [%s]\n      actual   [%s]\n' \
            "$name" "$expected" "$actual"
        FAILED=$((FAILED + 1))
    fi
}

printf '[test] unfurl binary: %s\n' "$UNFURL_BIN"
"$UNFURL_BIN" --help >/dev/null 2>&1 || :

# 1) domains: 逐行输出主机名, 保留重复项
assert_eq "domains (保留重复)" \
    "example.net,sub.example.com,sub.example.com" \
    "$(run_mode domains)"

# 2) --unique: 去重后仅剩两个不同域名, 验证 -u/--unique 语义
assert_eq "domains --unique (去重)" \
    "example.net,sub.example.com" \
    "$(run_mode --unique domains)"

# 3) apexes: sub.example.com 归并到注册域 example.com
assert_eq "apexes -u (注册域提取)" \
    "example.com,example.net" \
    "$(run_mode -u apexes)"

# 4) paths
assert_eq "paths (路径提取)" \
    "/about,/orgs,/users" \
    "$(run_mode paths)"

# 5) keys: query string 的键
assert_eq "keys (查询串键)" \
    "id,name,org" \
    "$(run_mode keys)"

# 6) values: query string 的值
assert_eq "values (查询串值)" \
    "123,ExCo,Sam" \
    "$(run_mode values)"

printf '\n'
if [ "$FAILED" -ne 0 ]; then
    printf 'unfurl test.sh: %d/%d case(s) FAILED\n' "$FAILED" "$TOTAL"
    exit 1
fi
printf 'unfurl test.sh: all %d cases PASS\n' "$TOTAL"
