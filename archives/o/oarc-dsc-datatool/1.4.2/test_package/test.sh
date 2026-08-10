#!/usr/bin/env bash
# oarc-dsc-datatool 1.4.2 test_package smoke test
# Verifies module import, version, core classes (Dataset/Dimension/Input/Output/
# Generator/Transformer), functional Dataset/Dimension behavior, and plugin
# module presence (R34: test() must call self.run, substantive dependency).
#
# 7 smoke test assertions:
#   1. import dsc_datatool — module import
#   2. __version__ == "1.4.2" — version assertion
#   3. Dataset class exists and is a class — Dataset class presence
#   4. Dimension class exists and is a class — Dimension class presence
#   5. Input/Output/Generator/Transformer base classes exist — core plugin base classes
#   6. Dataset() repr matches expected format — functional Dataset behavior
#   7. Dimension('test') repr matches expected format — functional Dimension behavior

set -euo pipefail

echo "=== oarc-dsc-datatool 1.4.2 Smoke Test ==="

# Test 1: Module import
echo "--- Test 1: Module import ---"
python3 -c "
import dsc_datatool
print('dsc_datatool imported successfully')
"

# Test 2: Version assertion
echo "--- Test 2: Version assertion ---"
python3 -c "
import dsc_datatool
print('dsc_datatool version:', dsc_datatool.__version__)
assert dsc_datatool.__version__ == '1.4.2', f'Expected 1.4.2, got {dsc_datatool.__version__}'
print('Version assertion: PASS')
"

# Test 3: Dataset class existence
echo "--- Test 3: Dataset class existence ---"
python3 -c "
from dsc_datatool import Dataset
import inspect
assert inspect.isclass(Dataset), 'Dataset is not a class'
print('Dataset class exists: PASS')
"

# Test 4: Dimension class existence
echo "--- Test 4: Dimension class existence ---"
python3 -c "
from dsc_datatool import Dimension
import inspect
assert inspect.isclass(Dimension), 'Dimension is not a class'
print('Dimension class exists: PASS')
"

# Test 5: Input/Output/Generator/Transformer base classes exist
echo "--- Test 5: Input/Output/Generator/Transformer base classes ---"
python3 -c "
from dsc_datatool import Input, Output, Generator, Transformer
import inspect
assert inspect.isclass(Input), 'Input is not a class'
assert inspect.isclass(Output), 'Output is not a class'
assert inspect.isclass(Generator), 'Generator is not a class'
assert inspect.isclass(Transformer), 'Transformer is not a class'
print('Input/Output/Generator/Transformer base classes: PASS')
"

# Test 6: Dataset() repr matches expected format
echo "--- Test 6: Dataset functional behavior ---"
python3 -c "
from dsc_datatool import Dataset
o = Dataset()
assert '%r' % o == '<Dataset name=None dimension=[]>', f'Unexpected repr: {repr(o)}'
print('Dataset() repr assertion: PASS')
"

# Test 7: Dimension('test') repr matches expected format
echo "--- Test 7: Dimension functional behavior ---"
python3 -c "
from dsc_datatool import Dimension
o = Dimension('test')
assert \"%r\" % o == \"<Dimension name='test' value=None dimension=[]>\", f'Unexpected repr: {repr(o)}'
print('Dimension(\"test\") repr assertion: PASS')
"

echo ""
echo "=== All 7 smoke tests PASSED ==="
