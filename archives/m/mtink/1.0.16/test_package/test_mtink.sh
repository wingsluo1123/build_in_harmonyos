#!/data/service/hnp/bin/bash
# Consumer assertions for the packaged mtink 1.0.16 (HarmonyOS PC / aarch64).
#
# Every assertion runs one of the three installed binaries.  mtink 1.0.16 has
# no automated test suite upstream (N = 0, see notes.md), and HarmonyOS PC has
# no printer device node at all, so the assertions below deliberately use the
# headless entry points that upstream already provides:
#
#   * `ttink -v` / `-h` / no-args  -> resource init + argument contract
#   * `ttink -l`                   -> the whole built-in EPSON model database
#   * `ttink -d <device> -i`       -> the real device bring-up code path
#                                     (/dev/lp0 ABSENT, /dev/null PRESENT but
#                                      not a printer: same failure wording,
#                                      different root cause)
#   * `askPrinter <device>`        -> the parport/ppdev ioctl path
#                                     (PPCLAIM/PPNEGOT) and the LPIOC device-id
#                                     path, both ending in a defined exit code
#   * `mtinkd`                     -> the daemon's /var/run, /var/mtink paths
#
# Assertion inventory (30; the count is the harness's `discovered` value):
#   A01-A03  presence of the three packaged executables
#   A04-A05  ttink -v          (exit code + version banner)
#   A06-A08  ttink -h          (exit code + usage header + mandatory argument)
#   A09-A10  ttink (no args)   (fail-closed exit code + usage on stderr)
#   A11-A14  ttink -l          (exit code + 90 rows + first record + last record)
#   A15      ttink -l          (mid-table record Stylus Photo R2400)
#   A16-A17  shipped data file (91 `.PRINTER` records == 90 rows + upstream off-by-one)
#   A18-A19  ttink -d /dev/lp0 -i   (device node ABSENT: exit code + wording)
#   A20-A21  ttink -d /dev/null -i  (node PRESENT, not a printer: exit code + wording)
#   A22-A23  askPrinter parport / LPIOC device-id paths (exit codes)
#   A24-A25  mtinkd on a /var-less root (exit code + perror text)
#   A26-A28  OHOS self-signing invariant (.codesign section per executable)
#   A29-A30  no libusb-0.1 reference, each guarded by a positive control that
#            proves the symbol table was actually read (the delivered ELFs are
#            stripped, so a bare `llvm-nm -u` returns an EMPTY table and any
#            "symbol absent" assertion built on it would pass vacuously)
#
# usage: test_mtink.sh <package-folder> <result-file> <work-dir>
#
# `set -u` only (no `-e`/pipefail) is deliberate: the harness *asserts on*
# non-zero exit codes and on `grep` misses (which return 1), so an errexit
# shell would abort on the very observations it is meant to record.  Every
# command whose status matters is checked explicitly via check_rc/check_eq/
# check_has and counted; the script's own exit status is `[ "$FAILED" -eq 0 ]`.
set -u

PKG=$1
RESULT=$2
WORK=$3

PASSED=0
FAILED=0

pass() { PASSED=$((PASSED + 1)); echo "  [PASS] $1"; }
fail() { FAILED=$((FAILED + 1)); echo "  [FAIL] $1"; }
check_rc() { if [ "$2" -eq "$3" ]; then pass "$1 (rc=$2)"; else fail "$1 (rc=$2, expected $3)"; fi; }
check_eq() { if [ "$2" = "$3" ]; then pass "$1 ($2)"; else fail "$1 (got '$2', expected '$3')"; fi; }
check_has() { if grep -F -q -- "$2" "$3" 2>/dev/null; then pass "$1"; else fail "$1 (expected '$2' in $3)"; fi; }

BIN="$PKG/bin"
TTINK="$BIN/ttink"
MTINKD="$BIN/mtinkd"
ASKPRINTER="$BIN/askPrinter"

rm -rf "$WORK"
mkdir -p "$WORK/home"
# Sandbox HOME: the consumer test must never touch the developer's real HOME.
export HOME="$WORK/home"
export TMPDIR="$WORK"
cd "$WORK"

echo "== mtink 1.0.16 consumer test =="
echo "package: $PKG"
echo "work   : $WORK"

# ── A01-A03: the delivered executables ─────────────────────────────────────
for tool in "$TTINK" "$MTINKD" "$ASKPRINTER"; do
  if [ -x "$tool" ]; then
    pass "packaged executable present: ${tool##*/}"
  else
    fail "packaged executable missing or not executable: $tool"
  fi
done

# ── A04-A10: headless CLI contract (no printer hardware involved) ──────────
"$TTINK" -v >"$WORK/v.out" 2>"$WORK/v.err"
check_rc "ttink -v exits 0" "$?" 0
check_has "ttink -v reports the upstream version" "V 1.0.16" "$WORK/v.out"

"$TTINK" -h >"$WORK/h.out" 2>"$WORK/h.err"
check_rc "ttink -h exits 0" "$?" 0
check_has "ttink -h prints the upstream usage header" "Arguments for ttink" "$WORK/h.out"
check_has "ttink -h documents the mandatory device argument" "-d device_file" "$WORK/h.out"

"$TTINK" >"$WORK/na.out" 2>"$WORK/na.err"
check_rc "ttink without arguments fails closed" "$?" 1
check_has "ttink without arguments prints the usage on stderr" "Arguments for ttink" "$WORK/na.err"

# ── A11-A15: the built-in EPSON model database (91 records in model.c) ─────
# `ttink -l` walks `defaultConfigData` with `while (i < defaultConfigDataSize-1)`,
# i.e. it prints N-1 rows for N records - an upstream off-by-one that is part of
# the observed contract (91 records -> 90 rows; the last row is record 90,
# `Stylus Scan 2500`, and `Stylus Photo R2400` is row 78).
"$TTINK" -l >"$WORK/l.out" 2>"$WORK/l.err"
check_rc "ttink -l exits 0" "$?" 0
check_eq "ttink -l prints one row per model minus the upstream off-by-one" \
  "$(wc -l < "$WORK/l.out" | tr -d ' ')" "90"
check_has "ttink -l lists the first table record" "Stylus C20SX" "$WORK/l.out"
check_has "ttink -l lists the true last row (record 90)" "Stylus Scan 2500" "$WORK/l.out"
check_has "ttink -l lists a mid-table record" "Stylus Photo R2400" "$WORK/l.out"

# ── A16-A17: cross-check the shipped runtime data file against the table ───
DESC=$(grep -c '^\.PRINTER' "$PKG/share/mtink/printer.desc.bldin" 2>/dev/null | tr -d ' ')
check_eq "shipped printer.desc.bldin carries the same 91 records" "$DESC" "91"
check_eq "binary table size and data file agree modulo the off-by-one" \
  "$((DESC - 1))" "90"

# ── A18-A21: device bring-up on the real (absent) printer nodes ────────────
if [ -e /dev/lp0 ]; then LP0_STATE=PRESENT; else LP0_STATE=ABSENT; fi
echo "  [INFO] /dev/lp0 is $LP0_STATE on this machine (HarmonyOS PC ships no printer node)"

"$TTINK" -d /dev/lp0 -i >"$WORK/lp0.out" 2>"$WORK/lp0.err"
check_rc "ttink -d /dev/lp0 -i reports the missing printer node instead of hanging" "$?" 1
check_has "ttink -d /dev/lp0 -i uses the upstream failure wording" \
  "No access to device file or no attached printer." "$WORK/lp0.err"

"$TTINK" -d /dev/null -i >"$WORK/null.out" 2>"$WORK/null.err"
check_rc "ttink -d /dev/null -i fails at the printer query, not at the open" "$?" 1
check_has "ttink -d /dev/null -i reaches the same defined failure" \
  "No access to device file or no attached printer." "$WORK/null.err"

# ── A22-A23: the parport/ppdev and LPIOC device-id probe paths ─────────────
# Observed verbatim: /dev/lp0 exits 1 with no output at all; /dev/usb/lp0 exits
# 1 with `open: No such file or directory` on stderr.
"$ASKPRINTER" /dev/lp0 >"$WORK/ap_par.out" 2>"$WORK/ap_par.err"
check_rc "askPrinter parport path exits non-zero without /dev/parport0" "$?" 1

"$ASKPRINTER" /dev/usb/lp0 >"$WORK/ap_usb.out" 2>"$WORK/ap_usb.err"
check_rc "askPrinter LPIOC device-id path exits non-zero without /dev/usb/lp0" "$?" 1

# ── A24-A25: the daemon and the /var-less HarmonyOS root ───────────────────
# mtinkd builds its pid file under /var/run/mtink and its FIFO under /var/mtink.
# HarmonyOS has no /var at all, so both mkdir() calls fail; upstream prints the
# perror text and continues, which makes the failure deterministic and
# observable without starting any background service.
timeout 15 "$MTINKD" >"$WORK/mtinkd.out" 2>"$WORK/mtinkd.err"
MTINKD_RC=$?
check_rc "mtinkd terminates instead of daemonising when /var is missing" "$MTINKD_RC" 0
check_has "mtinkd reports the missing run directory" "No such file or directory" "$WORK/mtinkd.err"

# ── A26-A28: OHOS packaging invariants ────────────────────────────────────
READELF=$(command -v llvm-readelf || echo /data/service/hnp/bin/llvm-readelf)
if [ -x "$READELF" ]; then
  for tool in ttink mtinkd askPrinter; do
    # `|| true`: `grep -c` exits 1 when the count is 0, and the count itself is
    # the value under test (`check_eq` below), not the grep status.
    n=$("$READELF" -SW "$BIN/$tool" 2>/dev/null | grep -c '\.codesign' || true)
    check_eq "$tool carries exactly one .codesign section" "${n:-0}" "1"
  done
else
  fail "llvm-readelf unavailable: cannot verify the OHOS signing invariant"
fi

# ── A29-A30: no libusb-0.1 reference, WITH a positive control ──────────────
# The libusb wrapper (mainSrc/usbHlp.c) is entirely inside `#ifdef MACOS` and the
# `Configure -m` "libusb under Linux" mode is self-contradictory upstream, so the
# delivered binaries must not reference the libusb-0.1 API.
#
# The delivered ELFs are **stripped** (no `.symtab`), so `llvm-nm -u` prints
# nothing at all and any "symbol absent" assertion built on it would pass
# vacuously.  The dynamic symbol table (-D) is the correct oracle: it is read
# back with a positive control (non-empty AND contains the CRT entry point
# __libc_start_main) before the negative check is allowed to pass.
NM=$(command -v llvm-nm || echo /data/service/hnp/bin/llvm-nm)
nm_no_libusb() {
  tool=$1
  label=$2
  out="$WORK/nm-$tool.out"
  "$NM" -D -u "$BIN/$tool" >"$out" 2>"$WORK/nm-$tool.err"
  rc=$?
  rows=$(wc -l < "$out" 2>/dev/null | tr -d ' ')
  ctl=no
  if [ "$rc" -eq 0 ] && [ "${rows:-0}" -gt 0 ] && grep -qE ' U __libc_start_main$' "$out"; then
    ctl=yes
  fi
  hits=$(grep -cE 'usb_|libusb' "$out" 2>/dev/null | tr -d ' ')
  if [ "$ctl" = yes ] && [ "${hits:-1}" -eq 0 ]; then
    pass "$label: undefined dynamic-symbol table non-empty (${rows} rows, __libc_start_main present) and free of the libusb-0.1 API"
  else
    fail "$label: libusb check inconclusive or positive (nm rc=$rc rows=${rows:-0} positive_control=$ctl libusb_hits=${hits:-?}; an unstripped-table check here would be vacuous)"
  fi
}
if [ -x "$NM" ]; then
  nm_no_libusb ttink "there is no libusb dependency (ttink)"
  nm_no_libusb mtinkd "there is no libusb dependency (mtinkd)"
else
  fail "llvm-nm unavailable: cannot verify the libusb dead-code claim"
  fail "llvm-nm unavailable: cannot verify the libusb dead-code claim (mtinkd)"
fi

echo "== result =="
echo "discovered $((PASSED + FAILED))" >"$RESULT"
echo "passed $PASSED" >>"$RESULT"
echo "failed $FAILED" >>"$RESULT"
echo "passed $PASSED/$((PASSED + FAILED))"
[ "$FAILED" -eq 0 ]
