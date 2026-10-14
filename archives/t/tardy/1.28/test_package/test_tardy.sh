#!/bin/sh
# Consumer contract test for tardy 1.28 (tool package).
# Runs the installed `tardy` binary (on PATH via conanrun env):
#  1. `tardy -version` reports 1.28
#  2. `tardy -help` exits 0
#  3. Functional roundtrip: build a tar with the system tar, add a prefix
#     with tardy, and confirm the member name changed on the other side.
set -u
fail=0

check() {
    n="$1"; shift
    if "$@"; then
        echo "ok $n - $*"
    else
        echo "not ok $n - $*"
        fail=$((fail + 1))
    fi
}

check 1 sh -c 'tardy -version 2>&1 | grep -q "1\.28"'
check 2 tardy -help >/dev/null 2>&1

work="${TMPDIR:-/tmp}/tardy-test-$$"
mkdir -p "$work" && cd "$work" || exit 1
# tardy only understands the GNU tar header layout.  The platform's toybox tar
# emits POSIX/ustar headers that tardy rejects with
# `corrupted uid field {tar-posix}`, and toybox has no `--format=gnu`, so
# synthesise the fixture with Python's tarfile (available on the device).
python3 - <<'PY' || { echo "not ok 3 - could not build the GNU tar fixture"; fail=$((fail + 1)); }
import io, tarfile
payload = b'hello tardy\n'
buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode='w', format=tarfile.GNU_FORMAT) as tf:
    info = tarfile.TarInfo('member.txt')
    info.size = len(payload)
    info.mode = 0o644
    info.mtime = 0
    tf.addfile(info, io.BytesIO(payload))
with open('in.tar', 'wb') as fh:
    fh.write(buf.getvalue())
PY
[ -s in.tar ] || { echo "not ok 3 - fixture archive missing"; fail=$((fail + 1)); }
if [ -s in.tar ] && tardy -prefix "P_" in.tar out.tar >/dev/null 2>&1; then
    # tardy joins the prefix as a path component, so "P_" + "member.txt"
    # becomes "P_/member.txt" (not "P_member.txt").
    check 3 sh -c 'tar -tf out.tar | grep -qx "P_/member.txt"'
else
    echo "not ok 3 - tardy -prefix roundtrip"
    fail=$((fail + 1))
fi
cd / && rm -rf "$work"

if [ "$fail" -eq 0 ]; then
    echo "TARDY_TEST PASS"
    exit 0
fi
echo "TARDY_TEST FAIL ($fail failure(s))"
exit 1
