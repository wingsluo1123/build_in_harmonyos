#!/usr/bin/env bash
# test_package/test_wallabag.sh — L0c test source + negative-control harness.
# Runs the PHP consumer checks, then proves the harness can catch failures
# (toybox lesson): a deliberately corrupted copy of a real bundle file MUST
# fail `php -l`. If it unexpectedly passes, the harness is blind -> fail.
set -euo pipefail

PHP="$1"
SHARE="$2"
TDIR="$(dirname "$0")"

echo "[test] php version"
"$PHP" --version

echo "[test] wallabag consumer checks"
"$PHP" "$TDIR/test_wallabag.php" "$SHARE"

echo "[test] negative control: corrupted file must fail php -l"
TMP_DIR="${TMPDIR:-/tmp}"
NEG="$TMP_DIR/wallabag-neg-probe.php"
cp "$SHARE/src/Wallabag/CoreBundle/Tools/Utils.php" "$NEG"
printf '\n{{{SYNTAX_BREAKAGE_FOR_HARNESS_PROBE>>>\n' >> "$NEG"
if "$PHP" -l "$NEG" >/dev/null 2>&1; then
    echo "[FAIL] negative control: broken file passed php -l, harness is blind"
    rm -f "$NEG"
    exit 1
else
    echo "[ok] negative control: broken file rejected by php -l"
fi
rm -f "$NEG"

echo "[test] wallabag test_package: PASS"
