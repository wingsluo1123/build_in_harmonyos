#!/data/service/hnp/bin/bash
# test_package/test.sh — fdm 2.2 消费者验证（在 conanrun 环境下真实执行随包 bin/fdm）
#
# 组 1  随包二进制存在且可执行
# 组 2  usage 参数面：真实执行 `fdm -h`，断言上游 usage 文本与退出码
# 组 3  端到端 fetch → deliver（核心流程）：本地 maildir 源 → fdm 抓取 →
#       规则匹配 → 投递到 mbox 目标；断言投递内容与源端被取走
# 组 4  反例对照：同一规则集下，主题不匹配的邮件不得投递到任何目标
#
# 平台垫片：LD_PRELOAD=$FDM_TEST_SHIM（见 fdm-test-passwd.c 头注释）——
# OHOS /etc/passwd 无当前 uid 条目，补这一条才能让 fdm 走到 fetch/deliver。
set -u

FDM="${FDM_BIN:?FDM_BIN 未设置}"
SHIM="${FDM_TEST_SHIM:?FDM_TEST_SHIM 未设置}"
WORK="${FDM_TEST_WORK:?FDM_TEST_WORK 未设置}"

[ -f "$SHIM" ] || { echo "[FAIL] 平台垫片不存在: $SHIM" >&2; exit 1; }
export LD_PRELOAD="$SHIM"
export FDM_TEST_PWDIR="$WORK"

CHECK_N=0
ok()   { CHECK_N=$((CHECK_N + 1)); echo "[OK]   #$CHECK_N $*"; }
fail() { echo "[FAIL] #$((CHECK_N + 1)) $*" >&2
         echo "ASSERTIONS: $CHECK_N passed, 1 failed"; exit 1; }
ck()   { desc="$1"; shift; if "$@"; then ok "$desc"; else fail "$desc"; fi; }

# 断言辅助（每个都会成为一条独立断言）
empty_dir()      { [ -z "$(ls -A "$1" 2>/dev/null)" ]; }
not_exist()      { [ ! -e "$1" ]; }
not_grep()       { ! grep -Eq "$1" "$2"; }
no_trace()       { ! grep -rq "$2" "$1" 2>/dev/null; }

mkdir -p "$WORK" || { echo "[FAIL] 无法建立工作目录 $WORK" >&2; exit 1; }
cd "$WORK" || { echo "[FAIL] 无法进入 $WORK" >&2; exit 1; }

echo "=== [1/4] 随包二进制 ==="
ck "随包 fdm 存在: $FDM" test -f "$FDM"
ck "随包 fdm 可执行位已置" test -x "$FDM"

echo "=== [2/4] usage 参数面（真实执行） ==="
"$FDM" -h >"$WORK/usage.log" 2>&1
rc=$?
echo "--- exit=$rc ---"; sed -n '1,3p' "$WORK/usage.log"
ck "usage 打印上游 usage 文本" grep -q "^usage: fdm" "$WORK/usage.log"
ck "usage 列出子命令 fetch|poll|cache" grep -q "fetch|poll|cache" "$WORK/usage.log"
ck "上游 usage() 退出码为 1（实得 $rc）" test "$rc" -eq 1
ck "启动期无 loader 报错" not_grep 'Error loading shared library|Error relocating' "$WORK/usage.log"

echo "=== [3/4] 端到端 fetch → deliver（本地 maildir → mbox） ==="
P="$WORK/pos"
rm -rf "$P"; mkdir -p "$P/src/new" "$P/src/cur" "$P/src/tmp"
cat > "$P/src/new/msg1" <<'MAIL'
Return-Path: <alice@example.com>
From: alice@example.com
To: bob@example.com
Subject: fdm consumer e2e 2422
Date: Thu, 15 Oct 2026 00:00:00 +0000
Message-Id: <e2e-2422-1@example.com>

BODY-POSITIVE-SENTINEL
MAIL
cat > "$P/fdm.conf" <<EOF
set maximum-size 10M
set lock-file "$P/fdm.lock"
account "src" maildir "$P/src"
action "dst" mbox "$P/dst.mbox"
match "^Subject: fdm consumer e2e 2422" in headers action "dst"
match all action drop
EOF
"$FDM" -v -f "$P/fdm.conf" fetch >"$P/fetch.log" 2>&1
rc=$?
echo "--- fdm fetch exit=$rc ---"; tail -6 "$P/fetch.log"
ck "fdm fetch 真实执行且退出码 0（实得 $rc）" test "$rc" -eq 0
ck "投递目标 mbox 已生成且非空" test -s "$P/dst.mbox"
ck "mbox 保留原始 From 头" grep -q "^From: alice@example.com" "$P/dst.mbox"
ck "mbox 保留原始 Subject 头" grep -q "^Subject: fdm consumer e2e 2422" "$P/dst.mbox"
ck "mbox 含完整正文（body sentinel）" grep -q "^BODY-POSITIVE-SENTINEL$" "$P/dst.mbox"
ck "mbox 含 fdm 本次投递痕迹（Received: by ... account \"src\"）" \
   grep -q '^Received: by .*(fdm .*account "src")' "$P/dst.mbox"
ck "源 maildir new/ 已被取空（证明真抓取而非空转）" empty_dir "$P/src/new"
ck "源 maildir cur/ 未被写入" empty_dir "$P/src/cur"
ck "抓取/投递过程无 loader 报错" not_grep 'Error loading shared library|Error relocating' "$P/fetch.log"

echo "=== [4/4] 反例对照（不匹配的邮件不得投递） ==="
N="$WORK/neg"
rm -rf "$N"; mkdir -p "$N/src/new" "$N/src/cur" "$N/src/tmp"
cat > "$N/src/new/msg1" <<'MAIL'
Return-Path: <mallory@example.com>
From: mallory@example.com
To: bob@example.com
Subject: fdm consumer e2e NOMATCH
Date: Thu, 15 Oct 2026 00:00:01 +0000
Message-Id: <e2e-nomatch-1@example.com>

BODY-NEGATIVE-SENTINEL
MAIL
cat > "$N/fdm.conf" <<EOF
set maximum-size 10M
set lock-file "$N/fdm.lock"
account "src" maildir "$N/src"
action "dst" mbox "$N/dst.mbox"
match "^Subject: fdm consumer e2e 2422" in headers action "dst"
match all action drop
EOF
"$FDM" -v -f "$N/fdm.conf" fetch >"$N/fetch.log" 2>&1
rc=$?
echo "--- fdm fetch exit=$rc ---"; tail -4 "$N/fetch.log"
ck "反例 fetch 真实执行且退出码 0（实得 $rc）" test "$rc" -eq 0
ck "不匹配邮件未生成投递目标 mbox" not_exist "$N/dst.mbox"
ck "工作目录内无该邮件正文的任何落盘副本" no_trace "$N" "BODY-NEGATIVE-SENTINEL"
ck "不匹配邮件被 catch-all 规则丢弃（源 maildir 取空）" empty_dir "$N/src/new"

echo "ALL TESTS PASSED"
echo "ASSERTIONS: $CHECK_N passed, 0 failed"
