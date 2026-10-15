#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer test for kati/0_git20251208 (ckati)
# Runs in conanrun env (PATH includes installed bin/); invoked via
# CONFIG_SHELL injected by test_package conanfile (shebang itself unused).
set -euo pipefail

# HMDFS: mktemp -d 建立 0700 目录，group 写位问题同 upx/termrec 先例，
# 用 chmod 770 恢复可写。
td="$(mktemp -d)"
chmod 770 "$td"
[ -w "$td" ] || { echo "FAIL temp dir not writable after chmod"; exit 1; }
trap 'rm -rf "$td"' EXIT
cd "$td"

cat > message.in <<EOF
payload
EOF

cat > Makefile <<'EOF'
OUT = $(patsubst %.mid,%.txt,$(subst .in,.mid,$(SRC)))
SRC = message.in

all: $(OUT)

%.mid: %.in
	@echo "pat $<" >> recipe-runs.log
	@cp $< $@

$(OUT): $(subst .in,.mid,$(SRC)) rule.stamp
	@echo "out $@" >> recipe-runs.log
	@echo "kati says: $(shell echo hello)-$(word 2,one two)" > $@
	@touch $@

rule.stamp:
	@echo "stamp" >> recipe-runs.log
	@echo stamped > $@
	@touch $@

.PHONY: all
EOF

echo "== [1/3] ckati: full evaluation of a real Makefile =="
ckati --use_find_emulator SHELL="$(command -v bash)" > run1.log 2>&1 || {
  cat run1.log; echo "FAIL ckati first run exited nonzero"; exit 1;
}
# 目标链 all -> message.txt -> message.mid(模式规则) -> message.in:
# message.txt 直接依赖 message.mid,模式规则才能实例化(真机 r3 实证:
# 直接依赖 message.in 时 .mid 永不被建,GNU make 同病,平台无关)。
[ -f message.mid ] || { echo "FAIL pattern rule did not produce message.mid"; exit 1; }
[ "$(cat message.mid)" = "payload" ] || { echo "FAIL message.mid content wrong"; exit 1; }
[ -f rule.stamp ] || { echo "FAIL prerequisite rule.stamp missing"; exit 1; }
got="$(cat message.txt)"
exp="kati says: hello-two"
[ "$got" = "$exp" ] || { echo "FAIL message.txt='$got' want '$exp' (functions/automatic vars wrong)"; exit 1; }
echo "OK artifacts correct: pattern rule + \$(subst)/\$(patsubst)/\$(shell)/\$(word) semantics"

echo "== [2/3] ckati regen check: second run must not re-execute recipes =="
# 直接计量 recipe 执行次数:每个 recipe 向 recipe-runs.log 追加一行标记。
# no-op 重跑后行数必须不变——这才是 regen 检测的直接断言,与 kati/make
# 的 "Nothing to be done" 横幅措辞解耦(真机 r3 实证:run1 全 @ 静默 0 行,
# run2 反而打 1 行横幅,横幅方向与旧注释假设相反,旧行数断言必假)。
[ "$(wc -l < recipe-runs.log)" -eq 3 ] || {
  echo "FAIL first run should execute exactly 3 recipes:"; cat recipe-runs.log; exit 1;
}
before="$(cat message.txt)"
ckati --use_find_emulator SHELL="$(command -v bash)" > run2.log 2>&1 || {
  cat run2.log; echo "FAIL ckati second run exited nonzero"; exit 1; }
after="$(cat message.txt)"
[ "$before" = "$after" ] || { echo "FAIL output changed on no-op rerun"; exit 1; }
[ "$(wc -l < recipe-runs.log)" -eq 3 ] || {
  echo "FAIL no-op rerun re-executed recipes:"; cat recipe-runs.log; exit 1;
}
echo "OK incremental no-op rerun is stable"

echo "== [3/3] ckati failure surface: missing prerequisite must fail =="
cat > bad.mk <<'EOF'
all: missing-dep.txt
	@echo never > $@
EOF
if ckati -f bad.mk SHELL="$(command -v bash)" > bad.log 2>&1; then
  echo "FAIL ckati accepted a Makefile with no rule for prerequisite"; exit 1
fi
grep -q "No rule to make target" bad.log || {
  echo "FAIL unexpected error message:"; cat bad.log; exit 1;
}
echo "OK missing-prerequisite error surfaces correctly"

echo "ALL TESTS PASSED"
