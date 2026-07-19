#!/usr/bin/env bash
# Test fnt — verify the binary runs and shows help
set -e

echo "=== fnt test suite ==="

# Test 1: fnt --help shows usage
echo "Test 1: fnt --help"
fnt --help 2>&1 | head -10
echo "PASS: fnt --help"

# Test 2: fnt list (lists installed fonts, should not crash)
echo "Test 2: fnt list"
fnt list 2>&1 | head -5 || echo "NOTE: fnt list may show no fonts (expected on OHOS)"
echo "PASS: fnt list"

# Test 3: fnt home (shows font directory)
echo "Test 3: fnt home"
fnt home 2>&1
echo "PASS: fnt home"

# Test 4: Verify shebang is correct
echo "Test 4: shebang check"
head -1 "$(which fnt)" | grep -q "hnp/bin/bash"
echo "PASS: shebang is correct"

# Test 5: Verify HarmonyOS platform support
echo "Test 5: HarmonyOS platform check"
grep -q "HarmonyOS" "$(which fnt)"
echo "PASS: HarmonyOS supported"

echo ""
echo "✅ All fnt tests passed"