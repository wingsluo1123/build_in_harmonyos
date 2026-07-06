#!/bin/sh
# Functional test for datamash — verifies core data processing operations
# Usage: sh test.sh <datamash_binary>
BIN="$1"
TMP=$(mktemp 2>/dev/null || printf '/tmp/datamash_test_%d' $$)

# Create test data: three rows with value column
printf "1\n2\n3\n" > "$TMP"

# Test 1: sum (1+2+3=6)
RESULT=$("$BIN" sum 1 < "$TMP")
if [ "$RESULT" != "6" ]; then
    rm -f "$TMP"
    exit 1
fi

# Test 2: count (3 rows)
RESULT=$("$BIN" count 1 < "$TMP")
if [ "$RESULT" != "3" ]; then
    rm -f "$TMP"
    exit 1
fi

# Test 3: max (max=3)
RESULT=$("$BIN" max 1 < "$TMP")
if [ "$RESULT" != "3" ]; then
    rm -f "$TMP"
    exit 1
fi

rm -f "$TMP"
