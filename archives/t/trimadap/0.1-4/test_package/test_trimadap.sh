#!/bin/sh
# trimadap 0.1-4 消费者测试 —— 真实执行被测二进制（R34）
#
# 用法: sh test_trimadap.sh <trimadap-mt 绝对路径> <test_package 目录>
#
# 断言来源（非"跑一遍回填"）：
#   A. 构造型用例：输入由"插入片段 + 已知接头"拼接而成，期望掩码/剪切结果按构造直接推导
#   B. 上游 oracle：Homebrew 的 `brew test trimadap` 断言 test.fa 上第 4 个默认接头
#      ATCTCGTATGCCGTCTTCTGCTTG 的命中数为 1（该断言来自 x86 SSE2 构建，本适配在
#      aarch64 标量路径下必须复现）
#   C. 结构不变量：掩码模式下输出长度不变、非 X 区与输入逐字符相同、X 区连续且贴合某一端
#   D. 精确后缀用例：read 1/read 6 的接头是输入读段的精确后缀，期望值运行时由输入推导
set -eu
if (set -o pipefail) 2>/dev/null; then
	set -o pipefail
fi

BIN=${1:?trimadap-mt path is required}
PKG=${2:?test_package directory is required}

if [ ! -x "$BIN" ]; then
	printf 'trimadap binary is not executable: %s\n' "$BIN" >&2
	exit 1
fi

WORK="$(mktemp -d "${TMPDIR:-.}/trimadap-test.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT HUP INT TERM

PASS=0
FAIL=0

pass() {
	PASS=$((PASS + 1))
	printf '  ok   : %s\n' "$1"
}

fail() {
	FAIL=$((FAIL + 1))
	printf '  FAIL : %s\n' "$1" >&2
}

assert_str() { # assert_str <label> <expected> <actual>
	if [ "$2" = "$3" ]; then
		pass "$1"
	else
		fail "$1"
		printf '         expected: %s\n         actual  : %s\n' "$2" "$3" >&2
	fi
}

assert_file() { # assert_file <label> <expected-file> <actual-file>
	if cmp -s "$2" "$3"; then
		pass "$1"
	else
		fail "$1"
		diff -u "$2" "$3" >&2 || true
	fi
}

xs() { # xs <n> — 打印 n 个 X
	printf "%0${1}d" 0 | tr '0' 'X'
}

# ---------------------------------------------------------------- 构造型输入
# 70 bp 插入片段；接头均取自上游 illumina.txt 的 TruSeq 序列
PAY70="ACTCCTGACCTCCTGATCCGCCCGCCTCGGCCTCCCAAACTGCTGGGATTACAGGCGTGAGCCACCACG"
AD3FULL="AGATCGGAAGAGCACACGTCTGAACTCCAGTCAC"          # illumina.txt 3'-end primer 1
AD3MISM="AGATCGGTAGAGCACACGTCTGAACTCCAGTCAC"          # 同上，单碱基错配
AD3PART="AGATCGGAAGAG"                                # 同上，仅前 12 bp
FIVE30="CTCTTTCCCTACACGACGCTCTTCCGATCT"               # illumina.txt 5'-end primer 后 30 bp
NOADAP="TGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCA"

{
	printf '>no_adapter\n%s\n' "$NOADAP"
	printf '>mismatch3p\n%s%s\n' "$PAY70" "$AD3MISM"
	printf '>short3p\n%s%s\n' "$PAY70" "$AD3PART"
	printf '>fiveprime\n%s%s\n' "$FIVE30" "$PAY70"
} > "$WORK/extra.fa"

# ---------------------------------------------------------------- 1. 版本
assert_str "-v 输出上游 VERSION 宏 (r11)" "r11" "$("$BIN" -v)"

# ---------------------------------------------------------------- 2. 上游 test.fa
"$BIN" "$PKG/test.fa" > "$WORK/up.out" 2> "$WORK/up.err"

# 2a. 结构不变量：长度不变、非 X 区与输入一致、X 区连续且贴合一端
awk 'FNR==NR { if (FNR % 2 == 0) in_[++n] = $0; next }
     FNR % 2 == 0 { m++; out_[m] = $0 }
     END {
	if (n != m) { printf "记录数不一致: in=%d out=%d\n", n, m; bad = 1 }
	for (i = 1; i <= n && i <= m; i++) {
		a = in_[i]; b = out_[i]
		if (length(a) != length(b)) {
			printf "read %d 长度改变: %d -> %d\n", i, length(a), length(b); bad = 1; continue
		}
		for (j = 1; j <= length(a); j++) {
			cb = substr(b, j, 1)
			if (cb != "X" && cb != substr(a, j, 1)) {
				printf "read %d 第 %d 位序列被修改\n", i, j; bad = 1; break
			}
		}
		fx = index(b, "X")
		if (fx > 0) {
			lx = fx
			for (j = fx; j <= length(b); j++) if (substr(b, j, 1) == "X") lx = j
			for (j = fx; j <= lx; j++) if (substr(b, j, 1) != "X") {
				printf "read %d 掩码不连续\n", i; bad = 1; break
			}
			if (!(fx == 1 || lx == length(b))) { printf "read %d 掩码未贴合任一端\n", i; bad = 1 }
		}
	}
	exit bad ? 1 : 0
     }' "$PKG/test.fa" "$WORK/up.out" > "$WORK/struct.txt" 2>&1 || true
if [ -s "$WORK/struct.txt" ]; then
	fail "结构不变量（长度/序列保真/掩码连续贴合端）"
	cat "$WORK/struct.txt" >&2
else
	pass "结构不变量（长度/序列保真/掩码连续贴合端，6 条读段）"
fi

# 2b. 上游 oracle：第 4 个默认接头命中数 = 1
assert_str "上游 oracle：接头 ATCTCGTATGCCGTCTTCTGCTTG 命中数=1" "1" \
	"$(awk '$2 == "ATCTCGTATGCCGTCTTCTGCTTG" { print $1 }' "$WORK/up.err")"

# 2c. read 1 / read 6：接头为输入读段的精确后缀，期望值运行时由输入推导
r1=$(sed -n '2p' "$PKG/test.fa")
p1=${r1%AGATCGGAAGAGCACACG}
if [ "$p1" = "$r1" ]; then
	fail "read 1 输入自检（应含 18 bp 接头后缀）"
else
	assert_str "read 1：精确后缀接头被整段掩码" "$p1$(xs 18)" "$(sed -n '2p' "$WORK/up.out")"
fi

r6=$(sed -n '12p' "$PKG/test.fa")
p6=${r6%AGATCGGAAG}
if [ "$p6" = "$r6" ]; then
	fail "read 6 输入自检（应含 10 bp 接头后缀）"
else
	assert_str "read 6：精确后缀接头被整段掩码" "$p6$(xs 10)" "$(sed -n '12p' "$WORK/up.out")"
fi

# 2d. 线程不变性
"$BIN" -p 4 "$PKG/test.fa" > "$WORK/up4.out" 2> /dev/null
assert_file "-p 4 与单线程输出逐字节一致" "$WORK/up.out" "$WORK/up4.out"

# ---------------------------------------------------------------- 3. 构造型用例（掩码模式）
"$BIN" "$WORK/extra.fa" > "$WORK/extra.out" 2> "$WORK/extra.err"

assert_str "对照读段（无接头）不被修改" "$NOADAP" "$(sed -n '2p' "$WORK/extra.out")"
assert_str "3' 接头单碱基错配仍被掩码" "$PAY70$(xs ${#AD3MISM})" "$(sed -n '4p' "$WORK/extra.out")"
assert_str "3' 接头仅 12 bp 前缀仍被掩码" "$PAY70$(xs ${#AD3PART})" "$(sed -n '6p' "$WORK/extra.out")"
assert_str "5' 接头（read 起始）被整段掩码" "$(xs ${#FIVE30})$PAY70" "$(sed -n '8p' "$WORK/extra.out")"

# ---------------------------------------------------------------- 4. 构造型用例（-t 剪切模式）
"$BIN" -t 8 "$WORK/extra.fa" > "$WORK/trim.out" 2> /dev/null
{
	printf '>no_adapter\n%s\n' "$NOADAP"
	printf '>mismatch3p\n%s\n' "$PAY70"
	printf '>short3p\n%s\n' "$PAY70"
	printf '>fiveprime\n%s\n' "$PAY70"
} > "$WORK/trim.expected"
assert_file "-t 8 精确剪切为插入片段" "$WORK/trim.expected" "$WORK/trim.out"

# ---------------------------------------------------------------- 5. 自定义接头 -3
"$BIN" -3 "$AD3FULL" "$WORK/extra.fa" > "$WORK/custom.out" 2> "$WORK/custom.err"
assert_str "-3 仅使用自定义接头（默认接头不再参与）" "$AD3FULL" \
	"$(awk '{ print $2 }' "$WORK/custom.err")"
assert_str "-3 模式下 5' 接头读段保持原样" "$FIVE30$PAY70" "$(sed -n '8p' "$WORK/custom.out")"

# ---------------------------------------------------------------- 汇总
printf 'trimadap functional test: %d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
