#!/bin/sh
# test_maybexs.sh — Consumer test for JSON::MaybeXS Perl module
#
# R34: Calls actual JSON::MaybeXS API (encode_json, decode_json)
# to validate functionality, not just a stub print.
#
# Usage: sh test_maybexs.sh <perl_lib_path>

set -eu

PERL_LIB="$1"

# Verify package files exist
if [ ! -d "$PERL_LIB" ]; then
    echo "ERROR: Perl lib directory not found: $PERL_LIB" >&2
    exit 1
fi

# Find MaybeXS.pm (could be in a subdirectory)
PM_FILE=$(find "$PERL_LIB" -name "MaybeXS.pm" -print -quit 2>/dev/null || true)
if [ -z "$PM_FILE" ]; then
    echo "ERROR: MaybeXS.pm not found in package" >&2
    exit 1
fi
echo "OK: Found MaybeXS.pm at $PM_FILE"

# Test 1: Load module and check version
RESULT=$(perl -I"$PERL_LIB" -MJSON::MaybeXS -e 'print $JSON::MaybeXS::VERSION' 2>&1) || {
    echo "ERROR: Failed to load JSON::MaybeXS: $RESULT" >&2
    exit 1
}
echo "OK: JSON::MaybeXS loaded, version: $RESULT"
[ -n "$RESULT" ] || { echo "ERROR: Version is empty" >&2; exit 1; }

# Test 2: Encode JSON (actual API call)
RESULT=$(perl -I"$PERL_LIB" -MJSON::MaybeXS=encode_json -e '
    my $json = encode_json({test => "value", number => 123});
    print $json;
' 2>&1) || {
    echo "ERROR: encode_json failed: $RESULT" >&2
    exit 1
}
echo "OK: encode_json works: $RESULT"
echo "$RESULT" | grep -q '"test":"value"' || { echo "ERROR: encode result mismatch" >&2; exit 1; }

# Test 3: Decode JSON (actual API call)
RESULT=$(perl -I"$PERL_LIB" -MJSON::MaybeXS=decode_json -e '
    my $data = decode_json(qq({"test":"value","number":123}));
    print $data->{test};
' 2>&1) || {
    echo "ERROR: decode_json failed: $RESULT" >&2
    exit 1
}
echo "OK: decode_json works: decoded test=$RESULT"
[ "$RESULT" = "value" ] || { echo "ERROR: decode result mismatch" >&2; exit 1; }

# Test 4: Boolean values (true/false/null)
RESULT=$(perl -I"$PERL_LIB" -MJSON::MaybeXS -e '
    my $json = encode_json({
        enabled => JSON::MaybeXS::true(),
        disabled => JSON::MaybeXS::false(),
    });
    print $json;
' 2>&1) || {
    echo "ERROR: boolean test failed: $RESULT" >&2
    exit 1
}
echo "OK: boolean encoding works: $RESULT"

# Test 5: Unicode support
RESULT=$(perl -I"$PERL_LIB" -MJSON::MaybeXS=encode_json -e '
    use Encode qw(encode_utf8);
    my $json = encode_json({name => "\x{5f20}\x{4e09}"});
    print encode_utf8($json);
' 2>&1) || {
    echo "ERROR: unicode test failed: $RESULT" >&2
    exit 1
}
echo "OK: unicode encoding works"

echo ""
echo "=== All JSON::MaybeXS tests passed ==="
