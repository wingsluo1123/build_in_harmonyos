#!/usr/bin/env bash
# cfgv 3.4.0 test script
# Smoke tests covering the core public API of cfgv (R34).
# Does NOT depend on pytest — uses python3 -c for each test.

set -euo pipefail

echo "=== cfgv 3.4.0 Smoke Test ==="

# ── Test 1: Module import + MISSING sentinel ──────────────────────
echo "--- Test 1: Module import + MISSING sentinel ---"
python3 -c "
import cfgv
from cfgv import MISSING
assert repr(MISSING) == 'MISSING', f'Expected MISSING, got {repr(MISSING)}'
print('cfgv imported, MISSING sentinel OK')
"

# ── Test 2: ValidationError str representation ────────────────────
echo "--- Test 2: ValidationError str ---"
python3 -c "
from cfgv import ValidationError
e = ValidationError('error msg')
assert str(e) == '\n=====> error msg', f'Unexpected str: {str(e)!r}'
print('ValidationError str: PASS')
"

# ── Test 3: validate() + Map + Required + check_bool (success) ───
echo "--- Test 3: validate Map/Required success ---"
python3 -c "
from cfgv import Map, Required, check_bool, validate
schema = Map('foo', 'key', Required('key', check_bool))
ret = validate({'key': True}, schema)
assert ret == {'key': True}
print('validate Map/Required: PASS')
"

# ── Test 4: validate() missing required key raises ValidationError ─
echo "--- Test 4: validate missing key raises ValidationError ---"
python3 -c "
from cfgv import Map, Required, check_bool, validate, ValidationError
schema = Map('foo', 'key', Required('key', check_bool))
try:
    validate({}, schema)
    raise AssertionError('Expected ValidationError')
except ValidationError as e:
    # error trace: At foo(key=MISSING) -> Missing required key: key
    assert 'Missing required key' in str(e), f'Unexpected: {str(e)!r}'
    print('ValidationError raised correctly: PASS')
"

# ── Test 5: Optional with default — apply_defaults / remove_defaults ─
echo "--- Test 5: Optional default + apply/remove_defaults ---"
python3 -c "
from cfgv import Map, Optional, check_bool, apply_defaults, remove_defaults, validate
map_optional = Map('foo', 'key', Optional('key', check_bool, False))
# missing optional -> default applied
ret = apply_defaults({}, map_optional)
assert ret == {'key': False}, f'Unexpected: {ret}'
# remove default -> back to {}
ret = remove_defaults({'key': False}, map_optional)
assert ret == {}, f'Unexpected: {ret}'
# explicit non-default preserved
ret = apply_defaults({'key': True}, map_optional)
assert ret == {'key': True}
print('Optional/apply_defaults/remove_defaults: PASS')
"

# ── Test 6: check_one_of rejects invalid value ─────────────────────
echo "--- Test 6: check_one_of rejection ---"
python3 -c "
from cfgv import check_one_of, ValidationError
try:
    check_one_of((1, 2))(3)
    raise AssertionError('Expected ValidationError')
except ValidationError as e:
    assert 'Expected one of 1, 2 but got: 3' == e.error_msg
    print('check_one_of rejection: PASS')
"

# ── Test 7: Array + validate (nested) ──────────────────────────────
echo "--- Test 7: Array validate ---"
python3 -c "
from cfgv import Array, Map, Required, check_bool, validate
schema = Array(Map('foo', 'id'))
validate([], schema)            # empty array OK
validate([{}], schema)          # single map OK
validate(({},), schema)         # tuple OK
print('Array validate: PASS')
"

echo ""
echo "=== All 7 tests PASSED ==="
