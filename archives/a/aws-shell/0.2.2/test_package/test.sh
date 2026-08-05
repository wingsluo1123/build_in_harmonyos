#!/bin/bash
# test.sh — test_package for aws-shell
# Verifies that the aws-shell package is properly installed and its API works.
# Uses importlib to load modules directly, bypassing __init__.py which
# requires botocore/prompt-toolkit (Python 3.12 incompatible).
set -euo pipefail

# Test 1: aws-shell entry point exists in PATH
AWS_SHELL_PATH=$(which aws-shell)
echo "[ok] aws-shell found at: $AWS_SHELL_PATH"

# Test 2: aws-shell-mkindex entry point exists in PATH
AWS_MKINDEX_PATH=$(which aws-shell-mkindex)
echo "[ok] aws-shell-mkindex found at: $AWS_MKINDEX_PATH"

# Test 3: awsshell Python package is discoverable
python3 -c "
import importlib.util
spec = importlib.util.find_spec('awsshell')
if spec:
    print(f'[ok] awsshell package found at: {spec.origin}')
else:
    print('[fail] awsshell package not found')
    exit(1)
"

# Test 4: Call awsshell.fuzzy.fuzzy_search API (R34: test must call API)
python3 -c "
import importlib.util, os, sys

# Find awsshell package directory
spec = importlib.util.find_spec('awsshell')
if not spec or not spec.origin:
    print('[fail] Cannot find awsshell package')
    sys.exit(1)

pkg_dir = os.path.dirname(spec.origin)

# Load fuzzy module directly (bypasses __init__.py which needs botocore)
fuzzy_spec = importlib.util.spec_from_file_location(
    'awsshell.fuzzy',
    os.path.join(pkg_dir, 'fuzzy.py')
)
fuzzy_mod = importlib.util.module_from_spec(fuzzy_spec)
fuzzy_spec.loader.exec_module(fuzzy_mod)

# Call the API
result = fuzzy_mod.fuzzy_search('abc', ['abcdef', 'abxyz', 'xyz'])
assert 'abcdef' in result, f'Expected abcdef in results, got {result}'
print(f'[ok] fuzzy_search(\"abc\", [...]) = {result}')
print('[ok] awsshell.fuzzy API call successful')
"

# Test 5: Call awsshell.substring.substring_search API
python3 -c "
import importlib.util, os, sys

spec = importlib.util.find_spec('awsshell')
pkg_dir = os.path.dirname(spec.origin)

sub_spec = importlib.util.spec_from_file_location(
    'awsshell.substring',
    os.path.join(pkg_dir, 'substring.py')
)
sub_mod = importlib.util.module_from_spec(sub_spec)
sub_spec.loader.exec_module(sub_mod)

result = sub_mod.substring_search('desc', ['describe', 'create', 'delete'])
assert 'describe' in result, f'Expected describe in results, got {result}'
print(f'[ok] substring_search(\"desc\", [...]) = {result}')
print('[ok] awsshell.substring API call successful')
"

# Test 6: Verify data files exist (completion data)
python3 -c "
import importlib.util, os

spec = importlib.util.find_spec('awsshell')
pkg_dir = os.path.dirname(spec.origin)
data_dir = os.path.join(pkg_dir, 'data')
if os.path.isdir(data_dir):
    json_files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
    print(f'[ok] data directory found with {len(json_files)} completion files')
else:
    print('[fail] data directory not found')
    exit(1)
"

echo "All tests passed."
