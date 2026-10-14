#!/bin/sh
# test_package/test.sh — qdl 2.7 消费者验证
#
# 这个包是**工具包**（没有库、没有公共头），所以"消费者"就是拿到 qdl 可执行
# 文件的人。验证按真实用法走：
#   1) 版本号必须是包版本 —— 钉住配方里 VERSION 选项的注入（上游用 git describe
#      推版本，tarball 里没有 .git，不钉就是 'unknown-version'）
#   2) 三个可执行文件都能起来并打印用法
#   3) 一次真实的、不需要 EDL 设备的业务：用与上游 tests/data 完全一致的
#      flat-build 固定装置跑 `qdl --dry-run --create-digests=...`，
#      并把生成的 VIP 表摘要与上游集成测试认的 EXPECTED_DIGEST 逐字节比对。
#
# 本脚本由 test_package/conanfile.py 用 bash 启动（OHOS 上 /system/bin/sh 是
# mksh，不能执行 ELF），所以这里用 POSIX 语法但可以放心依赖 bash 的行为。
export PATH="$PATH:/system/bin"

CHECKS=0
FAILED=0
pass() { CHECKS=$((CHECKS + 1)); echo "ok $CHECKS - $1"; }
fail() { CHECKS=$((CHECKS + 1)); FAILED=$((FAILED + 1)); echo "not ok $CHECKS - $1"; }

HERE=$(cd -- "$(dirname -- "$0")" && pwd -P)
WORK=$(mktemp -d "${TMPDIR:-/tmp}/qdl-consumer-XXXXXX") || {
    echo "Bail out! mktemp -d failed"; exit 1; }
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

echo "--- qdl 2.7 consumer verification ---"

# ---- 1. 版本 --------------------------------------------------------------
out=$(qdl --version 2>&1)
rc=$?
if [ "$rc" = "0" ] && echo "$out" | grep -q '2\.7'; then
    pass "qdl --version -> ${out}"
else
    fail "qdl --version rc=$rc output=[$out]"
fi

# ---- 2. 用法里必须列出真实存在的选项 --------------------------------------
if qdl --help > "$WORK/qdl-help.txt" 2>&1; then
    pass "qdl --help rc=0"
else
    fail "qdl --help failed rc=$?"
fi
for opt in --dry-run --create-digests --backend --serial; do
    if grep -q -- "$opt" "$WORK/qdl-help.txt"; then
        pass "qdl --help lists $opt"
    else
        fail "qdl --help does not list $opt"
    fi
done

# ---- 3. 另外两个可执行文件 ------------------------------------------------
for exe in qdl-ramdump qdl-ks; do
    if $exe --help > "$WORK/$exe.txt" 2>&1 && [ -s "$WORK/$exe.txt" ]; then
        pass "$exe --help produced usage"
    else
        fail "$exe --help failed (rc=$?)"
    fi
done

# ---- 4. 真实工作量：生成 VIP 表并与上游期望摘要比对 ------------------------
# 固定装置与上游 tests/data/generate_flat_build.sh 逐一对应：同样的 4 个 XML
# （随包放在 fixtures/）+ 同样的 9 个镜像文件名与大小。全部是稀疏的零字节
# 文件，所以 sha256 与上游 CI 上跑出来的完全一致。
FLAT="$WORK/flat"
VIP="$FLAT/vip"
mkdir -p "$FLAT" "$VIP"
cp "$HERE"/fixtures/*.xml "$FLAT"/

mkzero() { dd if=/dev/zero of="$FLAT/$1" bs=1024 count=0 seek="$2" 2>/dev/null; }
mkzero prog_firehose_ddr.elf 20
mkzero efi.bin 8192
mkzero gpt_backup0.bin 20
mkzero gpt_backup1.bin 20
mkzero gpt_main0.bin 24
mkzero gpt_main1.bin 24
mkzero rootfs.img 8192
mkzero xbl_config.elf 320
mkzero xbl.elf 800

# 与上游 test_vip_generation.sh 逐字相同的命令行（含 glob 展开顺序）。
( cd "$FLAT" && qdl --dry-run --create-digests="$VIP" \
      prog_firehose_ddr.elf rawprogram*.xml patch*.xml ) > "$WORK/vip.log" 2>&1
rc=$?
if [ "$rc" = "0" ]; then
    pass "qdl --dry-run --create-digests rc=0"
else
    fail "qdl --dry-run --create-digests rc=$rc"
    echo "--- vip.log ---"; sed 's/^/# /' "$WORK/vip.log"; echo "--- end ---"
fi

TABLE="$VIP/DigestsToSign.bin"
if [ -s "$TABLE" ]; then
    pass "VIP table produced ($(wc -c < "$TABLE") bytes)"
    got=$(sha256sum "$TABLE" | cut -d' ' -f1)
    want="3ca3c745c7bf60d9f51626ad819dce1e14788bc094c258da6656b0a469afbf15"
    if [ "$got" = "$want" ]; then
        pass "VIP table digest equals upstream EXPECTED_DIGEST ($got)"
    else
        fail "VIP table digest $got != upstream $want"
        echo "--- vip dir ---"; ls -l "$VIP" | sed 's/^/# /'; echo "--- end ---"
    fi
else
    fail "VIP table $TABLE missing or empty"
    echo "--- vip.log ---"; sed 's/^/# /' "$WORK/vip.log"; echo "--- end ---"
fi

echo "--- qdl consumer: $CHECKS checks run, $FAILED failed ---"
[ "$FAILED" = "0" ] || exit 1
echo "ALL CHECKS PASSED"
exit 0
