#!/bin/sh
# test_wiki_tui.sh — 消费者侧真实执行 wiki-tui 交付物（R34：真实执行 + 断言）
# 用法: sh test_wiki_tui.sh <pkg_dir>
set -u

PKG="${1:?usage: test_wiki_tui.sh <pkg_dir>}"
BIN="$PKG/bin/wiki-tui"
FAIL=0

say()  { printf '%s\n' "$*"; }
ok()   { say "  [ok] $*"; }
bad()  { say "  [FAIL] $*"; FAIL=1; }

say "== wiki-tui 交付物真实执行 =="
[ -x "$BIN" ] || { bad "binary not executable: $BIN"; exit 1; }

# ── ① --version 必须可用且报出 0.9.2 ─────────────────────────────────
if OUT=$("$BIN" --version 2>&1); then
  say "  --version → $(printf '%s' "$OUT" | head -1)"
  case "$OUT" in
    *0.9.2*) ok "--version 报出 0.9.2" ;;
    *)       bad "--version 未报出 0.9.2" ;;
  esac
else
  bad "--version 执行失败 rc=$?"
fi

# ── ② --help 必须可用且列出真实选项（--language / --config-path 等）──
if OUT=$("$BIN" --help 2>&1); then
  case "$OUT" in
    *--language*) ok "--help 列出 --language 选项" ;;
    *)            bad "--help 未见 --language 选项" ;;
  esac
else
  bad "--help 执行失败 rc=$?"
fi

# ── ③ --config-path（非 TUI 的纯 IO 路径，验证 config 解析真实可用）──
if OUT=$("$BIN" --config-path 2>&1); then
  case "$OUT" in
    */*) ok "--config-path 输出路径: $(printf '%s' "$OUT" | head -1)" ;;
    *)   bad "--config-path 未输出路径" ;;
  esac
else
  bad "--config-path 执行失败 rc=$?"
fi

# ── ④ 未知参数须以非零退出（clap 错误路径未被吞掉）──────────────────
if "$BIN" --definitely-not-a-flag >/dev/null 2>&1; then
  bad "未知参数竟以 0 退出"
else
  ok "未知参数以非零退出（错误路径正常）"
fi

say ""
if [ "$FAIL" -eq 0 ]; then
  say "OK: wiki-tui 交付物 4 项断言全部通过"
  exit 0
else
  say "FAILED: wiki-tui 交付物存在未通过断言"
  exit 1
fi
