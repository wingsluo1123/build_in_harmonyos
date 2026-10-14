#!/bin/sh
# test_package consumer test for unar 1.10.8.
# Verifies the installed unar/lsar binaries end to end:
#   1. --version for both tools
#   2. zip: list + extract + content verification
#   3. tar.gz: nested archive (gzip > tar) recognition + extract + content
set -e
export PATH="$PATH:/system/bin"

tmpdir=./.testpkg_tmp
rm -rf "$tmpdir"
mkdir -p "$tmpdir"

echo "--- unar consumer verification ---"

# 1. version info
out1=$(unar --version)
[ -n "$out1" ] || { echo "FAIL: unar --version produced no output"; exit 1; }
out2=$(lsar --version)
[ -n "$out2" ] || { echo "FAIL: lsar --version produced no output"; exit 1; }
echo "PASS 1: versions -> $out1 | $out2"

# 2. zip: create, list, extract, verify
python3 - "$tmpdir" <<'PYEOF'
import os, sys, zipfile
d = sys.argv[1]
with open(os.path.join(d, "hello.txt"), "w") as f:
    f.write("hello unar\n")
with zipfile.ZipFile(os.path.join(d, "test.zip"), "w", zipfile.ZIP_DEFLATED) as z:
    z.write(os.path.join(d, "hello.txt"), arcname="hello.txt")
PYEOF
lsar "$tmpdir/test.zip" | grep -q "hello.txt" || { echo "FAIL: lsar did not list zip entry"; exit 1; }
unar -f -o "$tmpdir/out" "$tmpdir/test.zip" >/dev/null || { echo "FAIL: unar zip extraction"; exit 1; }
[ -f "$tmpdir/out/hello.txt" ] || { echo "FAIL: zip extraction missing file"; exit 1; }
grep -q "hello unar" "$tmpdir/out/hello.txt" || { echo "FAIL: zip content mismatch"; exit 1; }
echo "PASS 2: zip list + extract + content"

# 3. tar.gz: nested archive (gzip > tar) recognition + extraction
python3 - "$tmpdir" <<'PYEOF'
import os, sys, tarfile
d = sys.argv[1]
with open(os.path.join(d, "a.txt"), "w") as f:
    f.write("alpha\n")
with tarfile.open(os.path.join(d, "test.tar.gz"), "w:gz") as t:
    t.add(os.path.join(d, "a.txt"), arcname="a.txt")
PYEOF
lsar "$tmpdir/test.tar.gz" | grep -q "Tar in Gzip" || { echo "FAIL: nested tar.gz not recognized by lsar"; exit 1; }
unar -f -o "$tmpdir/out2" "$tmpdir/test.tar.gz" >/dev/null || { echo "FAIL: unar tar.gz extraction"; exit 1; }
[ -f "$tmpdir/out2/a.txt" ] || { echo "FAIL: tar.gz extraction missing file"; exit 1; }
grep -q "alpha" "$tmpdir/out2/a.txt" || { echo "FAIL: tar.gz content mismatch"; exit 1; }
echo "PASS 3: tar.gz nested recognition + extract + content"

rm -rf "$tmpdir"
echo "test unar 1.10.8: 3/3 checks PASS"
exit 0
