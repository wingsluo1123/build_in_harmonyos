#!/bin/sh
# 模拟 Web 服务器以 CGI/1.1 方式调用 haserl 处理表单请求，
# 覆盖 GET query / POST urlencoded / POST multipart 三种真实请求路径。
set -u
HASERL="$1"
DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PAGE="$DIR/form.haserl"
TMP="$DIR/tmp_consumer"
mkdir -p "$TMP"
trap 'rm -rf "$TMP"' EXIT

pass=0; fail=0
check() {
    if grep -q "$2" "$3"; then
        echo "PASS: $1"
        pass=$((pass + 1))
    else
        echo "FAIL: $1 (期望输出包含: $2)"
        sed 's/^/    | /' "$3"
        fail=$((fail + 1))
    fi
}

# 用例 1：GET 请求，验证 QUERY_STRING 解析为 FORM_* 变量
REQUEST_METHOD=GET QUERY_STRING='name=harmonyos&num=42' \
    "$HASERL" "$PAGE" > "$TMP/get.out" 2>&1
check "GET 请求解析 QUERY_STRING (name)" "name=harmonyos" "$TMP/get.out"
check "GET 请求解析 QUERY_STRING (num)"  "num=42"         "$TMP/get.out"

# 用例 2：POST urlencoded，验证请求体表单解析
body='name=openharmony&num=2026'
printf '%s' "$body" | \
    REQUEST_METHOD=POST \
    CONTENT_TYPE='application/x-www-form-urlencoded' \
    CONTENT_LENGTH=$(printf '%s' "$body" | wc -c | tr -d ' ') \
    "$HASERL" "$PAGE" > "$TMP/post.out" 2>&1
check "POST urlencoded 解析表单 (name)" "name=openharmony" "$TMP/post.out"
check "POST urlencoded 解析表单 (num)"  "num=2026"         "$TMP/post.out"

# 用例 3：POST multipart/form-data，验证 rfc2388 解码器（适配核心代码路径）
printf '%b' '--HASEBOUNDARY\r\nContent-Disposition: form-data; name="name"\r\n\r\nharmonyos\r\n--HASEBOUNDARY--\r\n' > "$TMP/mp.body"
REQUEST_METHOD=POST \
    CONTENT_TYPE='multipart/form-data; boundary=HASEBOUNDARY' \
    CONTENT_LENGTH=$(wc -c < "$TMP/mp.body" | tr -d ' ') \
    "$HASERL" "$PAGE" < "$TMP/mp.body" > "$TMP/mp.out" 2>&1
check "POST multipart 解码表单字段" "name=harmonyos" "$TMP/mp.out"

echo "----"
echo "消费者用例: $((pass + fail)) 项断言, 通过 $pass 项, 失败 $fail 项"
[ "$fail" -eq 0 ]
