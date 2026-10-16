#!/bin/sh
# 消费者用例：运行 Conan 打包出的 tpaste 脚本，用确定性的假 curl 观测它对 curl 的调用。
# 用法: sh test_tpaste.sh <packaged tpaste>
set -u

TPASTE=$1
WORK=$(mktemp -d "${TMPDIR:-/tmp}/tpaste-test.XXXXXX") || exit 1
trap 'rm -rf "$WORK"' EXIT

PASS=0
FAIL=0
check() {
    # check <描述> <命令...>
    desc=$1
    shift
    if "$@"; then
        PASS=$((PASS + 1))
        echo "ok   - $desc"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL - $desc"
    fi
}

mkdir "$WORK/bin"
# 假 curl：逐行记录 argv，原样保存 stdin，向 stdout 输出固定 URL，退出码由 FAKE_CURL_RC 控制
cat > "$WORK/bin/curl" <<'EOF'
#!/bin/sh
: > "$FAKE_CURL_DIR/argv"
for a in "$@"; do printf '%s\n' "$a" >> "$FAKE_CURL_DIR/argv"; done
cat > "$FAKE_CURL_DIR/stdin"
echo "https://tpaste.us/AbCd"
exit "${FAKE_CURL_RC:-0}"
EOF
chmod 755 "$WORK/bin/curl"
export FAKE_CURL_DIR=$WORK
PATH="$WORK/bin:$PATH"
export PATH

# --- 1. 打包产物本身 ---
check "tpaste 已打包且可执行" test -x "$TPASTE"
check "shebang 为 #!/bin/sh" test "$(head -n 1 "$TPASTE")" = "#!/bin/sh"
printf '#!/bin/sh\n\nexec curl -sSF '"'"'tpaste=<-'"'"' https://tpaste.us' > "$WORK/expected"
check "脚本内容与上游 APKBUILD package() 的 printf 输出逐字节一致" cmp -s "$TPASTE" "$WORK/expected"

# --- 2. 直接执行（经 shebang），多行输入 ---
printf 'line1\nline2 with spaces\n\ttab\n' > "$WORK/in1"
FAKE_CURL_RC=0 "$TPASTE" < "$WORK/in1" > "$WORK/out1"
rc=$?
check "正常执行退出码为 0" test "$rc" -eq 0
check "curl 参数第 1 项为 -sSF" test "$(sed -n 1p "$WORK/argv")" = "-sSF"
check "curl 参数第 2 项为 tpaste=<-" test "$(sed -n 2p "$WORK/argv")" = "tpaste=<-"
check "curl 参数第 3 项为 https://tpaste.us" test "$(sed -n 3p "$WORK/argv")" = "https://tpaste.us"
check "curl 参数恰好 3 项" test "$(wc -l < "$WORK/argv" | tr -d ' ')" -eq 3
check "stdin 原样转发给 curl" cmp -s "$WORK/in1" "$WORK/stdin"
check "curl 的 stdout 原样透传" test "$(cat "$WORK/out1")" = "https://tpaste.us/AbCd"

# --- 3. 无结尾换行 + NUL 以外的任意字节 ---
printf 'no-newline-tail \001\002 $HOME `x` "q" '"'"'s'"'"'' > "$WORK/in2"
sh "$TPASTE" < "$WORK/in2" > /dev/null
check "无结尾换行/特殊字符的输入字节级不变" cmp -s "$WORK/in2" "$WORK/stdin"

# --- 4. 空输入 ---
: > "$WORK/in3"
sh "$TPASTE" < "$WORK/in3" > /dev/null
check "空输入也会调用 curl 并转发空 stdin" test ! -s "$WORK/stdin"

# --- 5. exec 语义：curl 失败码原样传出 ---
FAKE_CURL_RC=22 sh "$TPASTE" < "$WORK/in1" > /dev/null
rc=$?
check "curl 退出码 22 原样传出" test "$rc" -eq 22

# --- 6. 命令行参数不会被注入到 curl ---
sh "$TPASTE" --evil "x y" < "$WORK/in1" > /dev/null
check "tpaste 忽略位置参数，不向 curl 追加" test "$(wc -l < "$WORK/argv" | tr -d ' ')" -eq 3

# --- 7. curl 不在 PATH 时脚本必须失败（依赖 curl，而非静默成功）---
EMPTY=$WORK/empty
mkdir "$EMPTY"
env PATH="$EMPTY" "$(command -v sh)" "$TPASTE" < "$WORK/in1" > /dev/null 2>&1
rc=$?
check "缺少 curl 时返回非 0" test "$rc" -ne 0

echo "passed=$PASS failed=$FAIL"
test "$FAIL" -eq 0
