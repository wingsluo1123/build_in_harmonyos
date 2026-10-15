#!/usr/bin/env bash
# kitchen 1.2.6 test script
# Smoke tests covering the core public API of kitchen (R34).
# Focuses on text.converters (used by taskw) and other key modules.

set -euo pipefail

echo "=== kitchen 1.2.6 Smoke Test ==="

# ── Test 1: Module import + __version__ ───────────────────────────
echo "--- Test 1: Module import + version ---"
python3 -c "
import kitchen
import kitchen.release
version = kitchen.release.__version__
assert version == '1.2.6', f'Expected 1.2.6, got {version!r}'
print('kitchen imported, version OK:', version)
"

# ── Test 2: kitchen.text.converters.to_unicode (taskw 依赖) ────────
echo "--- Test 2: kitchen.text.converters.to_unicode ---"
python3 -c "
import kitchen.text.converters

# Test bytes to unicode conversion
test_bytes = b'Hello, World!'
result = kitchen.text.converters.to_unicode(test_bytes)
assert isinstance(result, str), f'Expected str, got {type(result)}'
assert result == 'Hello, World!', f'Expected \"Hello, World!\", got {result!r}'

# Test with encoding errors (latin-1 bytes with utf-8 decoding)
latin1_bytes = b'\xe9\xe0\xe8'  # éàè in latin-1
result = kitchen.text.converters.to_unicode(latin1_bytes, encoding='utf-8')
assert isinstance(result, str), 'to_unicode should always return str'
print('kitchen.text.converters.to_unicode: PASS')
"

# ── Test 3: kitchen.text.converters.to_bytes ──────────────────────
echo "--- Test 3: kitchen.text.converters.to_bytes ---"
python3 -c "
import kitchen.text.converters

test_str = 'Hello, 世界!'
result = kitchen.text.converters.to_bytes(test_str)
assert isinstance(result, bytes), f'Expected bytes, got {type(result)}'
assert result == b'Hello, \xe4\xb8\x96\xe7\x95\x8c!', f'Unexpected bytes: {result!r}'
print('kitchen.text.converters.to_bytes: PASS')
"

# ── Test 4: kitchen.text.converters.getwriter ─────────────────────
echo "--- Test 4: kitchen.text.converters.getwriter ---"
python3 -c "
import kitchen.text.converters
import io

output = io.BytesIO()
writer = kitchen.text.converters.getwriter('utf-8')(output)
writer.write('Test 测试')
result = output.getvalue()
assert result == b'Test \xe6\xb5\x8b\xe8\xaf\x95', f'Unexpected output: {result!r}'
print('kitchen.text.converters.getwriter: PASS')
"

# ── Test 5: kitchen.i18n (internationalization support) ────────────
echo "--- Test 5: kitchen.i18n module exists ---"
python3 -c "
import kitchen.i18n
assert hasattr(kitchen.i18n, 'easy_gettext_setup'), 'easy_gettext_setup not found'
assert callable(kitchen.i18n.easy_gettext_setup), 'easy_gettext_setup not callable'
print('kitchen.i18n module: PASS')
"

# ── Test 6: kitchen.iterutils ─────────────────────────────────────
echo "--- Test 6: kitchen.iterutils.iterate ---"
python3 -c "
import kitchen.iterutils

# iterate() ensures the input is iterable
result = list(kitchen.iterutils.iterate('abc'))
assert result == ['abc'], f'Expected [\"abc\"], got {result}'

result = list(kitchen.iterutils.iterate(['a', 'b', 'c']))
assert result == ['a', 'b', 'c'], f'Expected [\"a\", \"b\", \"c\"], got {result}'

print('kitchen.iterutils.iterate: PASS')
"

# ── Test 7: kitchen.collections.StrictDict ────────────────────────
echo "--- Test 7: kitchen.collections.StrictDict ---"
python3 -c "
import kitchen.collections

d = kitchen.collections.StrictDict()
d[b'key'] = 'value1'
d['key'] = 'value2'
# StrictDict treats bytes and str as different keys
assert d[b'key'] == 'value1', f'Expected value1, got {d[b\"key\"]!r}'
assert d['key'] == 'value2', f'Expected value2, got {d[\"key\"]!r}'
assert len(d) == 2, f'Expected 2 keys, got {len(d)}'
print('kitchen.collections.StrictDict: PASS')
"

# ── Test 8: OHOS 鸿蒙特有测试 - Unicode 转换在鸿蒙环境 ─────────
echo "--- Test 8: OHOS Unicode conversion (HarmonyOS-specific) ---"
python3 -c "
import kitchen.text.converters
import sys
import platform

assert platform.system() == 'HarmonyOS', f'Expected HarmonyOS runtime, got {platform.system()}'
test_data = [
    (b'OHOS \xe9\x98\xbf\xe9\x87\x8c', 'utf-8'),  # OHOS 阿里
    (b'HarmonyOS \xe4\xb8\xad\xe6\x96\x87', 'utf-8'),  # HarmonyOS 中文
    (b'Binary data: \x00\x01\x02\x03', 'ascii'),  # Binary with non-ascii
]

for test_bytes, encoding in test_data:
    try:
        result = kitchen.text.converters.to_unicode(test_bytes, encoding=encoding, errors='replace')
        assert isinstance(result, str), f'to_unicode must return str, got {type(result)}'
        # Verify we can encode it back (lossy is OK due to errors='replace')
        result.encode('utf-8', errors='replace')
    except Exception as e:
        raise AssertionError(f'Failed on {test_bytes!r} with encoding {encoding}: {e}')

print(f'OHOS Unicode conversion test: PASS (Python {sys.version_info.major}.{sys.version_info.minor}, platform: {platform.system()})')
"

echo ""
echo "=== All 8 tests PASSED (including 1 OHOS-specific test) ==="
