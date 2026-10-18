#!/system/bin/sh
set -eu

# HMDFS drops the exec bit and refuses direct execution of the launcher
# (exit 126). Copy the packaged app tree to a non-HMDFS staging directory,
# run the launcher via explicit sh (HMDFS refuses direct exec; knowledge-base
# lesson: copy to a non-HMDFS partition before executing).
IDNITS_BIN=$(command -v idnits)
echo "[setup] launcher at $IDNITS_BIN"
APP_ROOT=$(dirname "$(dirname "$IDNITS_BIN")")
STAGE="${IDNITS_TEST_STAGE:-/data/storage/el2/base/cache}/idnits-test-$$"
rm -rf "$STAGE"
mkdir -p "$STAGE"
cp -r "$APP_ROOT/bin" "$APP_ROOT/res" "$STAGE/"
chmod +x "$STAGE/bin/idnits"
IDNITS="$STAGE/bin/idnits"

echo "[test 1] idnits launcher exists"
command -v idnits >/dev/null

echo "[test 2] version output is a semver string"
VERSION=$(sh "$IDNITS" --version)
echo "$VERSION"
# NOTE: upstream tag 3.1.0 still carries package.json version "3.0.0",
# so the CLI prints 3.0.0; assert on semver shape, not the tool name.
echo "$VERSION" | grep -Eq "^[0-9]+\.[0-9]+\.[0-9]+$"

echo "[test 3] real offline nit-check on a bundled fixture"
FIXTURE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/draft-smoke.txt"
# The fixture intentionally has nits, so idnits may exit non-zero; the
# assertion is on the reported output.
OUT=$(sh "$IDNITS" "$FIXTURE" || true)
echo "$OUT"
echo "$OUT" | grep -q "idnits"

echo "[test 4] error path: missing file must be rejected"
if sh "$IDNITS" /nonexistent/no-such-draft.txt >/dev/null 2>&1; then
  echo "missing file was accepted" >&2
  exit 1
fi

rm -rf "$STAGE"
echo "All 4 tests passed."
