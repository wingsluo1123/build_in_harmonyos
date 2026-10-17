#!/bin/sh
# Consumer end-to-end test for maildrop.
#
# Flow 1 (decode): the installed `reformime` decodes a real multipart message
# whose body part is ISO-8859-15, and the assertion is on the resulting UTF-8
# bytes — the raw ISO-8859-15 byte must be gone.
#
# Flow 2 (deliver): the installed `maildrop` delivers that message into a
# Maildir through a filter recipe, and the assertion is on the delivered
# message file: it must exist and still carry the original subject.
#
# Both flows fail loudly; the script exits non-zero if any check fails.
# `set -e` is deliberately not used: the checks are accounted for explicitly with
# `report $?`, so an early exit would hide the remaining results.
set -u
set -o pipefail

# The caller (test_package/conanfile.py) points this at the environment's
# temporary area, outside the archive under review, so that no run artefact can
# end up inside the package.
WORK="${WORKDIR:-$(pwd)/consumer-work}"
rm -rf "$WORK"
mkdir -p "$WORK"
cd "$WORK" || exit 1

failures=0

report() {
    if [ "$1" = "0" ]; then
        echo "PASS: $2"
    else
        echo "FAIL: $2"
        failures=$((failures + 1))
    fi
}

command -v reformime >/dev/null 2>&1
report $? "reformime from the package is on PATH"

command -v maildrop >/dev/null 2>&1
report $? "maildrop from the package is on PATH"

# ---------------------------------------------------------------------------
# Flow 1: decode an ISO-8859-15 body part to UTF-8.
# ---------------------------------------------------------------------------

cat > message.eml <<'MESSAGE'
Subject: consumer test
Mime-Version: 1.0
Content-Type: text/plain; charset=iso-8859-15
Content-Transfer-Encoding: quoted-printable

Price: =A4=A4=A4
MESSAGE

reformime -u < message.eml > decoded.out 2> decoded.err

# The euro sign is 0xA4 in ISO-8859-15 and E2 82 AC in UTF-8. Both patterns are
# matched as fixed strings: a raw byte used as a *regex* makes grep complain,
# and the complaint echoes those bytes, which a caller decoding this output as
# UTF-8 cannot handle.
euro=$(printf '\342\202\254\342\202\254\342\202\254')
grep -qF "Price: $euro" decoded.out
report $? "reformime decoded ISO-8859-15 0xA4 into UTF-8 euro signs"

# The unconverted byte must not survive anywhere in the output.
if LC_ALL=C grep -qF "$(printf '\244\244\244')" decoded.out 2>/dev/null; then
    report 1 "decoded output still contains the raw ISO-8859-15 bytes"
else
    report 0 "decoded output no longer contains the raw ISO-8859-15 bytes"
fi

# ---------------------------------------------------------------------------
# Flow 2: deliver the same message into a Maildir through a filter recipe.
# ---------------------------------------------------------------------------

mkdir -p maildir/cur maildir/new maildir/tmp
cat > filter <<'RECIPE'
to "./maildir"
RECIPE

# This filesystem cannot represent private permissions, so the recipe file's
# group bits cannot be cleared; accept that exposure explicitly (see notes.md).
MAILDROP_TRUST_FILTER_PERMS=1 \
LOGNAME=consumer \
HOME="$WORK" \
TMPDIR="${TMPDIR:-$WORK}" \
maildrop filter < message.eml > deliver.out 2> deliver.err
report $? "maildrop delivered the message without error"

delivered=$(find maildir/cur maildir/new -type f | wc -l)
if [ "$delivered" -ge 1 ]; then
    report 0 "Maildir received $delivered message file(s)"
else
    report 1 "Maildir received no message file"
fi

if grep -rq "Subject: consumer test" maildir/cur maildir/new 2>/dev/null; then
    report 0 "delivered message still carries the original subject"
else
    report 1 "delivered message does not carry the original subject"
fi

echo "--- reformime stderr ---"
cat decoded.err
echo "--- maildrop stderr ---"
cat deliver.err

if [ "$failures" -ne 0 ]; then
    echo "$failures consumer check(s) failed"
    exit 1
fi

echo "all consumer checks passed"
exit 0
