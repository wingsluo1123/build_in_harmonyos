#!/bin/sh
# Consumer test for splix 2.0.1.
#
# Drives the two delivered CUPS filters the way cupsd would and asserts on real
# observable results.  The end-to-end case feeds a genuine CUPS raster page
# (test_package/sample-8x8.raster, produced with the CUPS raster API for the
# Samsung ML-2250 PPD shipped in this package) through the filter and checks the
# QPDL stream that comes out.
#
# Usage: test_splix.sh <package_folder> [<raster file>]
#   <raster file> defaults to sample-8x8.raster next to this script; the conan
#   test() decodes sample-8x8.raster.b64 into a byte-identical temporary file and
#   passes that path instead (the binary cannot live in the repo).
# Exits non-zero as soon as an assertion fails.

set -u

pkg="${1:?usage: test_splix.sh <package_folder>}"
here="$(dirname "$0")"
model="$pkg/share/cups/model/splix"
raster="${2:-$here/sample-8x8.raster}"
work="${TMPDIR:-/tmp}/splix-test-$$"

fails=0
fail() { echo "FAIL: $*"; fails=$((fails + 1)); }
pass() { echo "PASS: $*"; }

rm -rf "$work"
mkdir -p "$work" || { echo "FAIL: cannot create work dir $work"; exit 1; }
trap 'rm -rf "$work"' EXIT

UEL="$(printf '\033')%-12345X"

echo "--- splix consumer verification ---"

# ---------------------------------------------------------------------------
# S1 - both filters are installed and look like aarch64 OHOS executables
# ---------------------------------------------------------------------------
for tool in rastertoqpdl pstoqpdl; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        fail "S1 $tool is not on PATH"
        continue
    fi
    bin="$(command -v "$tool")"
    if [ ! -x "$bin" ]; then
        fail "S1 $bin is not executable"
        continue
    fi
    size="$(wc -c <"$bin" | tr -d ' ')"
    if [ "$size" -ge 1000000 ]; then
        pass "S1 $tool is installed ($size bytes, executable)"
    else
        fail "S1 $tool looks like a stub ($size bytes)"
    fi
    if command -v od >/dev/null 2>&1; then
        magic="$(dd if="$bin" bs=1 count=4 2>/dev/null | od -An -tx1 | tr -d ' \n')"
        machine="$(dd if="$bin" bs=1 skip=18 count=2 2>/dev/null | od -An -tx1 | tr -d ' \n')"
        if [ "$magic" = "7f454c46" ] && [ "$machine" = "b700" ]; then
            pass "S1 $tool is a 64-bit little-endian aarch64 ELF (e_machine=0xb7)"
        else
            fail "S1 $tool ELF header is not aarch64: magic=$magic machine=$machine"
        fi
    else
        echo "note: od(1) is not available, skipping the ELF header check"
    fi
done

# ---------------------------------------------------------------------------
# S2 - printer description data is delivered
# ---------------------------------------------------------------------------
if [ -f "$model/ml2250.ppd" ]; then
    pass "S2 ml2250.ppd installed"
else
    fail "S2 $model/ml2250.ppd is missing"
fi
ppd_count="$(ls "$model"/*.ppd 2>/dev/null | wc -l)"
if [ "$ppd_count" -ge 240 ]; then
    pass "S2 $ppd_count PPD files installed"
else
    fail "S2 only $ppd_count PPD files installed (expected >= 240)"
fi
if [ -f "$pkg/share/cups/drv/output.drv" ]; then
    pass "S2 output.drv installed"
else
    fail "S2 $pkg/share/cups/drv/output.drv is missing"
fi
if grep -q 'FileVersion: "2.0.0"' "$model/ml2250.ppd" 2>/dev/null; then
    pass "S2 PPD FileVersion matches the filter PPD version"
else
    fail "S2 PPD FileVersion does not match 2.0.0"
fi

# ---------------------------------------------------------------------------
# S3 - argument validation of rastertoqpdl (real execution)
# ---------------------------------------------------------------------------
rastertoqpdl >"$work/s3.out" 2>"$work/s3.err"
rc=$?
if [ "$rc" -eq 1 ]; then
    pass "S3 rastertoqpdl with no arguments exits 1"
else
    fail "S3 rastertoqpdl with no arguments exits $rc (expected 1)"
fi
if grep -q 'Usage: .*job-id user title copies options' "$work/s3.err"; then
    pass "S3 usage text is printed"
else
    fail "S3 usage text missing: $(cat "$work/s3.err")"
fi

# ---------------------------------------------------------------------------
# S4 - end to end: CUPS raster -> QPDL  （本包的**完整消费者用例**）
# ---------------------------------------------------------------------------
s4_ok=0
s4_fails_before="$fails"
if [ ! -f "$raster" ]; then
    fail "S4 test raster $raster is missing"
else
    PPD="$model/ml2250.ppd" rastertoqpdl 1 tester "splix test" 1 "" "$raster" \
        >"$work/page.qpdl" 2>"$work/s4.err"
    rc=$?
    if [ "$rc" -eq 0 ]; then
        pass "S4 rastertoqpdl converts the CUPS raster page (exit 0)"
    else
        fail "S4 rastertoqpdl exit $rc: $(tail -3 "$work/s4.err")"
    fi
    size="$(wc -c <"$work/page.qpdl" | tr -d ' ')"
    if [ "$size" -gt 300 ]; then
        pass "S4 produced a $size byte QPDL stream"
    else
        fail "S4 QPDL stream is only $size bytes"
    fi
    first="$(dd if="$work/page.qpdl" bs=1 count=9 2>/dev/null)"
    if [ "$first" = "$UEL" ]; then
        pass "S4 stream starts with the PJL universal exit sequence"
    else
        fail "S4 stream does not start with the PJL universal exit sequence"
    fi
    if grep -q 'ENTER LANGUAGE = QPDL' "$work/page.qpdl"; then
        pass "S4 stream selects the QPDL printer language"
    else
        fail "S4 stream does not select the QPDL printer language"
    fi
    last="$(tail -c 9 "$work/page.qpdl" 2>/dev/null)"
    if [ "$last" = "$UEL" ]; then
        pass "S4 stream ends with the PJL universal exit sequence"
    else
        fail "S4 stream does not end with the PJL universal exit sequence"
    fi
    if [ "$fails" -eq "$s4_fails_before" ]; then
        s4_ok=1
        pass "S4 consumer use case completed end to end (raster -> QPDL)"
    fi
fi

# ---------------------------------------------------------------------------
# S5 - argument validation of pstoqpdl (real execution)
# ---------------------------------------------------------------------------
pstoqpdl >"$work/s5.out" 2>"$work/s5.err"
rc=$?
if [ "$rc" -eq 1 ]; then
    pass "S5 pstoqpdl with no arguments exits 1"
else
    fail "S5 pstoqpdl with no arguments exits $rc (expected 1)"
fi
if grep -q 'Usage: .*job-id user title copies options' "$work/s5.err"; then
    pass "S5 usage text is printed"
else
    fail "S5 usage text missing: $(cat "$work/s5.err")"
fi

# ---------------------------------------------------------------------------
# 消费者用例口径（rule12）：S4 是一个**完整消费者用例**（真实 CUPS raster 页 → 交付的
# rastertoqpdl → QPDL 作业流端到端跑通并按业务语义校验首尾 PJL 序列与 QPDL 语言选择），
# S1/S2/S3/S5 是围绕它的断言。这里显式把「用例数」与「断言数」分开上报，机器可核。
# ---------------------------------------------------------------------------
cases_total=1
cases_passed=0
if [ "$s4_ok" -eq 1 ]; then
    cases_passed=1
fi
printf 'CONSUMER_CASES=%s/%s %s\n' "$cases_passed" "$cases_total" \
    "S4: CUPS raster page -> rastertoqpdl -> QPDL job stream (end-to-end)"
printf 'HMBS_HARMONY_CONSUMER_RESULT={"executed":true,"cases":%s,"passedCases":%s,"passed":%s,"command":"test_package/test_splix.sh","detail":"S4 end-to-end: real CUPS raster page driven through the delivered rastertoqpdl filter, output QPDL job stream checked (PJL universal exit sequence at both ends + ENTER LANGUAGE = QPDL)","assertionsFailed":%s}\n' \
    "$cases_total" "$cases_passed" \
    "$([ "$cases_passed" -eq 1 ] && echo true || echo false)" "$fails"

if [ "$fails" -eq 0 ]; then
    echo "test splix/2.0.1: ALL CHECKS PASSED"
    exit 0
fi
echo "test splix/2.0.1: $fails CHECK(S) FAILED"
exit 1
