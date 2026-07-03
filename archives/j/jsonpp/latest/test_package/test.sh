#!/bin/sh
# test_package/test.sh — jsonpp smoke test
# Verifies that jsonpp binary can pretty-print JSON input

set -e

JSONPP="$1"

if [ -z "$JSONPP" ]; then
    echo "Usage: $0 <path-to-jsonpp>"
    exit 1
fi

# Test 1: Basic JSON pretty printing
output=$(echo '{"hello":"world","arr":[1,2,3]}' | "$JSONPP")
expected='{
  "hello": "world",
  "arr": [
    1,
    2,
    3
  ]
}'

if [ "$output" = "$expected" ]; then
    echo "PASS: Basic JSON pretty printing"
else
    echo "FAIL: Basic JSON pretty printing"
    echo "Expected: $expected"
    echo "Got: $output"
    exit 1
fi

# Test 2: Help flag
"$JSONPP" --help 2>&1 | grep -q "Usage" || {
    echo "FAIL: --help output"
    exit 1
}
echo "PASS: --help flag"

# Test 3: Multiple JSON objects
output=$(echo '{"a":1}
{"b":2}' | "$JSONPP")
echo "$output" | grep -q '"a": 1' || {
    echo "FAIL: Multiple JSON objects"
    exit 1
}
echo "PASS: Multiple JSON objects"

echo "All tests passed."
