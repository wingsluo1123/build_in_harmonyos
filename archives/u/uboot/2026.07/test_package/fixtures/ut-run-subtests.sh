#!/bin/sh
# Per-subtest ut runner for the OHOS sandbox u-boot test_package.
#
# Methodology = upstream pytest: test/py/conftest.py::generate_ut_subtest
# enumerates UNIT_TEST subtests from the linker-list symbols
# "_u_boot_list_2_ut_<suite>_2_<name>" (RE_UT_TEST_LIST) in u-boot.sym, and
# test/py/tests/test_ut.py::test_ut runs each one as 'ut <suite> <name>' in
# its own u-boot process. This matters on two counts:
#   * dm_test_post_run tears down all uclasses after every UTF_DM test, so a
#     single-process 'ut all' run has cross-test DM state pollution (bootstd
#     scans, usb/scsi/nand bindings) that upstream never observes;
#   * the bootstd suite additionally needs its fixture images (mmc1.img /
#     mmc4.img / flash1.img / mmc10.img / usb stick), built by mkfixtures.sh.
#
# Env:
#   U_BOOT_SANDBOX  path to the u-boot sandbox binary (required)
#   U_BOOT_DTB      path to arch/sandbox/dts/test.dtb (required)
#   U_BOOT_UT_PAIRS pre-generated subtest list (package test/pairs.txt;
#                   preferred — avoids shipping the large u-boot.sym)
#   U_BOOT_SYM      fallback: path to u-boot.sym from the build tree
#   UT_WORKDIR      scratch dir for logs + persistent data (default: ./ut-run)
#   U_BOOT_PERSISTENT_DATA_DIR  sandbox persistent data dir (default: UT_WORKDIR)
#
# Usage: sh ut-run-subtests.sh [suite] [first_idx last_idx]
#   suite: only that suite (default: all); indexes are 1-based over the
#          sorted full list
#
# Output contract: one verdict line per subtest
# ("TEST PASS|FAIL|SKIP: <suite> <name>"), then the final
# "TEST SUMMARY: <p> passed, <f> failed, <s> skipped" line (plus the
# aggregate "RANGE=..." line); exit code 1 if any subtest failed.
F=${UT_WORKDIR:-$(pwd)/ut-run}
U=${U_BOOT_SANDBOX:?set U_BOOT_SANDBOX}
DTB=${U_BOOT_DTB:?set U_BOOT_DTB}
SUITE=${1:-}
LO=$((${2:-1})); HI=${3:-999999}
export HOME=${HOME:-/tmp}
export TMPDIR=$F/tmp
export U_BOOT_PERSISTENT_DATA_DIR=${U_BOOT_PERSISTENT_DATA_DIR:-$F}
mkdir -p $F $F/tmp $F/logs
cd $F || exit 1
# membuf_readline（lib 套件）契约：CWD 下有 README（上游 pytest 的
# CWD=源码树根）；test_uboot.sh 已放入 fixtures/README 副本，独立使用时补上
[ -f README ] || cp "${HOST_FIXTURES:-/nonexistent}/README" README 2>/dev/null || \
	printf 'README placeholder (fixtures/README ships the real one)\n' > README

# enumerate "suite name" pairs: prefer the package's pre-generated list
# (same regex as upstream RE_UT_TEST_LIST; _norun entries are
# pytest-skipped too); fall back to u-boot.sym from the build tree
if [ -n "$U_BOOT_UT_PAIRS" ] && [ -f "$U_BOOT_UT_PAIRS" ]; then
  cp "$U_BOOT_UT_PAIRS" $F/pairs.txt
else
  awk '{ if (match($0, /_u_boot_list_2_ut_[a-zA-Z0-9_]+_2_[a-zA-Z0-9_]+$/)) { s = substr($0, RSTART, RLENGTH); sub(/^_u_boot_list_2_ut_/, "", s); if (s !~ /_norun$/) print s } }' \
    ${U_BOOT_SYM:?set U_BOOT_SYM} | sort -u > $F/pairs.txt
fi
[ -n "$SUITE" ] && grep "^${SUITE}_2_" $F/pairs.txt > $F/pairs.tmp && mv $F/pairs.tmp $F/pairs.txt
TOTAL=$(wc -l < $F/pairs.txt)
echo "subtests: $TOTAL (suite=${SUITE:-all})"
# full-run guard: the enumerated count is pinned (919 linker-list subtests
# as of 2026.07, incl. the SDL-gated video/cedit/expo surface). A silently
# converged-away test surface (e.g. the HOST_HAS_SDL probe failing) must
# fail loudly instead of sailing through with "All tests passed". Override
# for other trees: U_BOOT_EXPECT_SUBTESTS.
if [ -z "$SUITE" ] && [ "$LO" = 1 ] && [ "$HI" = 999999 ]; then
  [ "$TOTAL" = "${U_BOOT_EXPECT_SUBTESTS:-919}" ] || {
    echo "ERROR: expected ${U_BOOT_EXPECT_SUBTESTS:-919} subtests, enumerated $TOTAL" >&2
    exit 1
  }
fi

i=0; PASS=0; FAIL=0; SKIP=0; FLIST=""
while read -r pair; do
  [ -z "$pair" ] && continue
  i=$((i + 1))
  [ $i -lt "$LO" ] && continue
  [ $i -gt "$HI" ] && break
  s=${pair%%_2_*}; n=${pair#*_2_}
  log=$F/logs/${s}_${n}.log
  $U -d $DTB -c "ut $s $n; exit" < /dev/null > $log 2>&1
  if grep -aq "failures: 0" $log; then
    if grep -aq "skipped: [1-9]" $log; then
      SKIP=$((SKIP + 1))
      echo "TEST SKIP: $s $n"
    else
      PASS=$((PASS + 1))
      echo "TEST PASS: $s $n"
    fi
  else
    FAIL=$((FAIL + 1)); FLIST="$FLIST $s/$n"
    echo "TEST FAIL: $s $n"
  fi
done < $F/pairs.txt
echo "TEST SUMMARY: $PASS passed, $FAIL failed, $SKIP skipped (range $LO..$HI)"
echo "RANGE=$LO..$HI PASS=$PASS FAIL=$FAIL SKIP=$SKIP"
echo "failed:$FLIST"
[ "$FAIL" = "0" ] || exit 1
