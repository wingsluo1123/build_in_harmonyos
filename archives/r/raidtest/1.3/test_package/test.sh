#!/bin/sh
# Consumer tests for the installed raidtest binary (no pytest dependency).
# Records are little-endian: uint64 offset, uint32 length, uint8 type,
# padded to 16 bytes (upstream struct iorec).
set -u

BINDIR="${1:-${CONAN_TEST_PACKAGE_BIN:-}}"
[ -n "$BINDIR" ] || { echo "FAIL: no bin dir given (arg1 or CONAN_TEST_PACKAGE_BIN)"; exit 2; }
BIN="$BINDIR/raidtest"
[ -x "$BIN" ] || { echo "FAIL: $BIN not executable"; exit 2; }
SECTOR=512
MEDIA=4194304   # 4 MiB
MAXIO=131072
PASS=0
FAIL=0

ok() { PASS=$((PASS + 1)); echo "PASS: $1"; }
bad() { FAIL=$((FAIL + 1)); echo "FAIL: $1"; }

check() { # check <description> <expected:0|nonzero> <command...>
    desc="$1"; want="$2"; shift 2
    if "$@" >/dev/null 2>&1; then got=0; else got=nonzero; fi
    if [ "$got" = "$want" ]; then ok "$desc"; else bad "$desc"; fi
}

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
cd "$work" || exit 1

# 1. no arguments -> usage error
check "usage without args fails" nonzero "$BIN"
# 2. unknown subcommand -> usage error
check "unknown subcommand fails" nonzero "$BIN" nonsense
# 3. genfile without -n/-s fails
check "genfile without options fails" nonzero "$BIN" genfile
check "genfile without -s fails" nonzero "$BIN" genfile -n 10
# 4. -r and -w together rejected (genfile)
check "genfile -r -w rejected" nonzero "$BIN" genfile -r -w -n 10 -s "$MEDIA"
# 5. genfile happy path
check "genfile creates data file" 0 \
    "$BIN" genfile -s "$MEDIA" -S "$SECTOR" -n 100 data.bin
# 6. file collision without -f fails
check "genfile refuses clobber without -f" nonzero \
    "$BIN" genfile -s "$MEDIA" -n 10 data.bin
# 7. -f overwrites existing file (separate name: data.bin is re-verified below)
printf x > "$work/ow.bin"
check "genfile -f overwrites" 0 \
    "$BIN" genfile -f -s "$MEDIA" -n 10 ow.bin
# 8. read-only file contains only READ records
check "genfile -r read-only" 0 \
    "$BIN" genfile -r -s "$MEDIA" -S "$SECTOR" -n 16 ro.bin
# 9. record layout validation (python3 ships with the Conan runner)
if python3 - "$work" <<'EOF'
import struct, sys, os
rec = struct.Struct("<QIBxxx")
media, sector, maxio = 4194304, 512, 131072
for name, want_type in (("data.bin", None), ("ro.bin", 0)):
    raw = open(os.path.join(sys.argv[1], name), "rb").read()
    assert len(raw) % rec.size == 0, name
    n = 0
    for off, ln, t in rec.iter_unpack(raw):
        assert off % sector == 0, (name, off)
        assert ln % sector == 0 and 0 < ln <= maxio, (name, ln)
        assert off + ln <= media, (name, off, ln)
        if want_type is None:
            assert t in (0, 1), (name, t)
        else:
            assert t == want_type, (name, t)
        n += 1
    assert n in (100, 16), (name, n)
print("records-ok")
EOF
then ok "record layout valid"; else bad "record layout valid"; fi
# 10. genfile stdout counters
if "$BIN" genfile -r -s "$MEDIA" -n 4 cnt.bin | \
    grep -q "Number of WRITE requests: 0."; then
    ok "genfile stdout counters"; else bad "genfile stdout counters"; fi
# 11-13. test subcommand error paths (no block device needed)
check "test without -d fails" nonzero "$BIN" test data.bin
check "test with missing device fails" nonzero \
    "$BIN" test -d /dev/no-such-raidtest-device data.bin
check "test -r -w rejected" nonzero "$BIN" test -r -w -d /dev/null
check "test -n 0 rejected" nonzero "$BIN" test -d /dev/null -n 0

echo "test_package: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
