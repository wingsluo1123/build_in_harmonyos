#!/bin/bash
# test_package consumer test for fonttosfnt 1.2.5.
#
# 消费者视角验证：按 README/man 的真实用法调用已安装的 fonttosfnt 二进制，
# 把自带的最小 BDF 语料（font.bdf，4 个 glyph：space/zero/A/B）真正转换成
# .otb（sfnt 包装）文件，再逐项解析产物结构。
#
# fonttosfnt 与纯流式过滤器不同：writeFile() 用 fopen(filename, "wb+") 打开 -o
# 目标并在其中 fseek（写表目录后才回填 checksum），因此必须有一个可 seek 的真实
# 文件，不能像 bdftopcf 那样用 -o /dev/null 规避落盘。本脚本把产物写进
# $TMPDIR 下的 mktemp -d 临时目录并在退出时删除 —— 不往本目录（会被目录级
# git add 扫进提交，§12.71②）落任何文件。
set -u

pass=0
fail=0
ok()  { echo "PASS $1: $2"; pass=$((pass + 1)); }
bad() { echo "FAIL $1: $2"; fail=$((fail + 1)); }

echo "--- fonttosfnt 1.2.5 consumer verification ---"

# ── 可写 scratch 目录（-o 目标必须是可 seek 的真实文件）──
base="${TMPDIR:-.}"
d=$(mktemp -d "$base/fts.XXXXXX" 2>/dev/null) \
  || d=$(mktemp -d 2>/dev/null) \
  || d=.
trap 'rm -rf "$d"' 0 1 2 13 15
echo "scratch: $d"
otb="$d/out.otb"

# 取文件 offset/size 处的字节，输出连续小写 hex
hexat() { dd if="$1" bs=1 skip="$2" count="$3" 2>/dev/null | od -An -tx1 | tr -d ' \n'; }

# sfnt 表目录的 tag 抽取（断言 10/14 共用）。
# 只走「od 的十六进制文本」通道，再在纯 shell 里按表目录结构切片比对：
# 既不经 grep，也不把二进制塞进命令替换，因此不依赖具体实现。
# 为什么必须这么写：CI worker 的 PATH 里 /system/bin 的 toybox 0.8.12 grep 排在
# 前面，它对本产物的 208 字节表目录（含 NUL、无换行）用 -a -o -E 会静默返回空集
# （误差被 2>/dev/null 吞掉），而同一 worker 上 dd/od/tr 通道在断言 8/9/11 是可用的。
# sfnt 表目录：文件 offset 12 起，每表 16 字节 = 4 字节 tag + checksum + offset + length。
# $1 = sfnt 文件；$2 = numTables；输出形如 " EBDT EBLC "（空集输出空串）。
sfnt_tags() {
  local f=$1 n=$2 hexall dir i w out
  hexall=$(od -An -v -tx1 "$f" 2>/dev/null | tr -d ' \n')
  dir=" "
  i=0
  while [ "$i" -lt "$n" ]; do
    dir="$dir${hexall:$((24 + 32 * i)):8} "
    i=$((i + 1))
  done
  out=""
  # 13 个 tag 的十六进制形（od 输出小写）
  for w in EBDT:45424454 EBLC:45424c43 OS/2:4f532f32 PCLT:50434c54 \
           cmap:636d6170 glyf:676c7966 head:68656164 hhea:68686561 \
           hmtx:686d7478 loca:6c6f6361 maxp:6d617870 name:6e616d65 \
           post:706f7374; do
    case "$dir" in
      *" ${w##*:} "*) out="${out}${out:+ }${w%%:*}" ;;
    esac
  done
  if [ -n "$out" ]; then printf ' %s ' "$out"; fi
}

# ── 1. --version 与任务版本逐字一致（PACKAGE_STRING）──
out=$(fonttosfnt --version 2>&1)
rc=$?
if [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -q "fonttosfnt 1.2.5"; then
  ok 1 "--version -> [$out]"
else
  bad 1 "--version rc=$rc out=[$out]"
fi

# ── 2. --help 渲染用法 ──
out=$(fonttosfnt --help 2>&1)
rc=$?
if [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -q "Usage:" \
   && printf '%s' "$out" | grep -q "\-o font.otb"; then
  ok 2 "--help renders usage (rc=0)"
else
  bad 2 "--help rc=$rc out=[$out]"
fi

# ── 3. 缺 -o：非零退出 + 明确诊断 ──
err=$(fonttosfnt font.bdf 2>&1 >/dev/null)
rc=$?
if [ "$rc" -ne 0 ] && printf '%s' "$err" | grep -q "Missing required -o option"; then
  ok 3 "no -o -> rc=$rc + 'Missing required -o option'"
else
  bad 3 "no -o rc=$rc err=[$err]"
fi

# ── 4. 未知参数：非零退出 + Unknown argument ──
err=$(fonttosfnt --definitely-not-an-option 2>&1 >/dev/null)
rc=$?
if [ "$rc" -ne 0 ] && printf '%s' "$err" | grep -q "Unknown argument:"; then
  ok 4 "unknown arg -> rc=$rc + 'Unknown argument:'"
else
  bad 4 "unknown arg rc=$rc err=[$err]"
fi

# ── 5. -g 缺参数：非零退出 + Missing argument ──
err=$(fonttosfnt -g 2>&1 >/dev/null)
rc=$?
if [ "$rc" -ne 0 ] && printf '%s' "$err" | grep -q "Missing argument to"; then
  ok 5 "-g without value -> rc=$rc + 'Missing argument to'"
else
  bad 5 "-g without value rc=$rc err=[$err]"
fi

# ── 6-7. 真实转换：BDF -> .otb ──
fonttosfnt -o "$otb" font.bdf > "$d/conv.log" 2>&1
rc=$?
if [ "$rc" -eq 0 ] && [ -s "$otb" ]; then
  ok 6 "fonttosfnt -o out.otb font.bdf -> rc=0, product present"
else
  bad 6 "conversion rc=$rc log=[$(cat "$d/conv.log" 2>/dev/null)]"
fi

size=$(wc -c < "$otb" 2>/dev/null || echo 0)
if [ "$size" -gt 200 ]; then
  ok 7 "product size = ${size} bytes"
else
  bad 7 "product size = ${size} bytes (expected > 200)"
fi

# ── 8. sfnt 版本号 = 0x00010000（TrueType outline sfnt，writeDir 首字段）──
ver=$(hexat "$otb" 0 4)
if [ "$ver" = "00010000" ]; then
  ok 8 "sfnt version = 00 01 00 00"
else
  bad 8 "sfnt version hex=[$ver]"
fi

# ── 9. 表目录 numTables（offset 4，大端 2 字节）──
nt=$(hexat "$otb" 4 2)
if [ -z "$nt" ]; then
  ntnum=0
else
  ntnum=$((0x$nt))
fi
if [ "$ntnum" -eq 13 ]; then
  ok 9 "numTables = 13 (EBDT/EBLC/OS2/PCLT/cmap/glyf/head/hhea/hmtx/loca/maxp/name/post)"
else
  bad 9 "numTables = $ntnum (expected 13)"
fi

# ── 10. 表目录里的 tag 集合逐项齐备 ──
# tag 抽取走 sfnt_tags（od 十六进制文本通道），不经 grep —— 见其定义处说明。
if [ "$ntnum" -gt 0 ]; then
  tags=$(sfnt_tags "$otb" "$ntnum")
else
  tags=""
fi
missing=""
for t in EBDT EBLC OS/2 PCLT cmap glyf head hhea hmtx loca maxp name post; do
  case " $tags " in
    *" $t "*) ;;
    *) missing="$missing $t" ;;
  esac
done
if [ -z "$missing" ]; then
  ok 10 "all 13 table tags present in table directory"
else
  bad 10 "missing table tags:$missing (seen: $tags)"
fi

# ── 11. head 表 magicNumber = 0x5F0F3CF5（sfnt 规范固定值，证明 head 表真被写出）──
blob=$(od -An -tx1 "$otb" 2>/dev/null | tr -d ' \n')
case "$blob" in
  *5f0f3cf5*) ok 11 "head magicNumber 5F 0F 3C F5 present" ;;
  *)          bad 11 "head magicNumber 5F 0F 3C F5 not found" ;;
esac

# ── 12. stdin 路径（man 页：未给 font 参数则从 stdin 读 BDF）──
fonttosfnt -o "$d/stdin.otb" < font.bdf > "$d/stdin.log" 2>&1
rc=$?
v2=$(hexat "$d/stdin.otb" 0 4)
if [ "$rc" -eq 0 ] && [ "$v2" = "00010000" ]; then
  ok 12 "stdin -> out.otb rc=0, sfnt version ok"
else
  bad 12 "stdin rc=$rc hex=[$v2] log=[$(cat "$d/stdin.log" 2>/dev/null)]"
fi

# ── 13. 选项组合 -b -c -r -g 1 -m 2 全部被接受且产物仍是 sfnt ──
fonttosfnt -b -c -r -g 1 -m 2 -o "$d/opt.otb" font.bdf > "$d/opt.log" 2>&1
rc=$?
v3=$(hexat "$d/opt.otb" 0 4)
if [ "$rc" -eq 0 ] && [ "$v3" = "00010000" ] && [ -s "$d/opt.otb" ]; then
  ok 13 "-b -c -r -g 1 -m 2 -> rc=0, sfnt version ok"
else
  bad 13 "option combo rc=$rc hex=[$v3] log=[$(cat "$d/opt.log" 2>/dev/null)]"
fi

# ── 14. -g 0 -m 0 差分断言：不写可缩放字形/度量 ⇒ 表目录里没有 glyf/loca ──
fonttosfnt -g 0 -m 0 -o "$d/g0.otb" font.bdf > "$d/g0.log" 2>&1
rc=$?
n0=$(hexat "$d/g0.otb" 4 2)
if [ -n "$n0" ]; then n0num=$((0x$n0)); else n0num=0; fi
tags0=""
if [ "$n0num" -gt 0 ]; then
  # 同断言 10：走 sfnt_tags 的 od 十六进制通道
  tags0=$(sfnt_tags "$d/g0.otb" "$n0num")
fi
# 空集守卫：抽不到 tag 即视为解析路径失效（判 FAIL），
# 否则「没有 glyf/loca」会被空集白送（这正是 CI 上断言 14 假 PASS 的成因）。
has_glyf=0
has_loca=0
case " $tags0 " in *" glyf "*) has_glyf=1 ;; esac
case " $tags0 " in *" loca "*) has_loca=1 ;; esac
if [ "$rc" -eq 0 ] && [ "$n0num" -eq 10 ] \
   && [ "$n0num" -lt "$ntnum" ] \
   && [ -n "$tags0" ] \
   && [ "$has_glyf" -eq 0 ] \
   && [ "$has_loca" -eq 0 ]; then
  ok 14 "-g 0 -m 0 -> rc=0, numTables=$n0num (< $ntnum), no glyf/loca"
else
  bad 14 "-g 0 -m 0 rc=$rc numTables=$n0num tags=[$tags0] log=[$(cat "$d/g0.log" 2>/dev/null)]"
fi

# ── 15. 损坏输入：非零退出 + 明确诊断（不静默吞错）──
printf 'this is not a bdf font\n' > "$d/bogus.bdf"
err=$(fonttosfnt -o "$d/bogus.otb" "$d/bogus.bdf" 2>&1 >/dev/null)
rc=$?
if [ "$rc" -ne 0 ] && printf '%s' "$err" | grep -q "Couldn't open face"; then
  ok 15 "corrupt input -> rc=$rc + \"Couldn't open face\""
else
  bad 15 "corrupt input rc=$rc err=[$err]"
fi

# ── 16. 输入文件不存在：非零退出 + 明确诊断 ──
err=$(fonttosfnt -o "$d/miss.otb" __fonttosfnt_missing_input__.bdf 2>&1 >/dev/null)
rc=$?
if [ "$rc" -ne 0 ] && printf '%s' "$err" | grep -q "Couldn't open face"; then
  ok 16 "missing input -> rc=$rc + \"Couldn't open face\""
else
  bad 16 "missing input rc=$rc err=[$err]"
fi

echo "test fonttosfnt 1.2.5: $pass/$((pass + fail)) checks PASS"
[ "$fail" -eq 0 ] || exit 1
exit 0
