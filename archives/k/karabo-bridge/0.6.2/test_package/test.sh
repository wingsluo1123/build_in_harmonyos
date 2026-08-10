#!/usr/bin/env bash
# karabo-bridge 0.6.2 test_package smoke test
# Verifies module import, version, Client/Sender classes, and serialize round-trip (R34)
#
# 5 smoke test assertions:
#   1. import karabo_bridge — module import
#   2. __version__ == "0.6.2" — version assertion
#   3. Client class exists and is a class — Client class instantiation
#   4. ServerInThread class exists and is a class — Sender/Server class presence
#   5. serialize/deserialize round-trip — simulated bridge pipeline data receive

set -euo pipefail

echo "=== karabo-bridge 0.6.2 Smoke Test ==="

# Test 1: Module import
echo "--- Test 1: Module import ---"
python3 -c "
import karabo_bridge
print('karabo_bridge imported successfully')
"

# Test 2: Version assertion
echo "--- Test 2: Version assertion ---"
python3 -c "
import karabo_bridge
print('karabo_bridge version:', karabo_bridge.__version__)
assert karabo_bridge.__version__ == '0.6.2', f'Expected 0.6.2, got {karabo_bridge.__version__}'
print('Version assertion: PASS')
"

# Test 3: Client class existence
echo "--- Test 3: Client class existence ---"
python3 -c "
from karabo_bridge import Client
import inspect
assert inspect.isclass(Client), 'Client is not a class'
print('Client class exists: PASS')
"

# Test 4: ServerInThread / Sender class existence
echo "--- Test 4: ServerInThread class existence ---"
python3 -c "
from karabo_bridge import ServerInThread
from karabo_bridge.server import Sender
import inspect
assert inspect.isclass(ServerInThread), 'ServerInThread is not a class'
assert inspect.isclass(Sender), 'Sender is not a class'
print('ServerInThread/Sender class exists: PASS')
"

# Test 5: serialize/deserialize round-trip (simulated bridge pipeline)
echo "--- Test 5: serialize/deserialize round-trip ---"
python3 -c "
import numpy as np
from karabo_bridge import serialize, deserialize

# Simulate data that would be sent over the Karabo bridge pipeline
data = {
    'source1': {
        'parameter.1.value': 123,
        'parameter.2.value': 1.23,
        'list.of.int': [1, 2, 3],
        'string.param': 'True',
        'boolean': False,
        'metadata': {'timestamp.tid': 9876543210, 'timestamp': 12345678},
    },
    'XMPL/DET/MOD0': {
        'image.data': np.random.randint(255, size=(2, 3, 4), dtype=np.uint8),
        'something.else': ['a', 'bc', 'd'],
    },
}

# Serialize data into ZMQ multipart payload
msg = serialize(data, protocol_version='2.2')
assert isinstance(msg, list), f'serialize should return a list, got {type(msg)}'

# Deserialize back — simulating what Client.next() does
d, m = deserialize(msg)
assert 'source1' in d, 'source1 missing from deserialized data'
assert 'XMPL/DET/MOD0' in d, 'XMPL/DET/MOD0 missing from deserialized data'
assert d['source1']['parameter.1.value'] == 123, 'parameter.1.value mismatch'
assert d['source1']['list.of.int'] == [1, 2, 3], 'list.of.int mismatch'
assert m['source1'] == {'timestamp.tid': 9876543210, 'timestamp': 12345678}, 'metadata mismatch'
assert m['XMPL/DET/MOD0'] == {}, 'XMPL/DET/MOD0 metadata should be empty'
print('serialize/deserialize round-trip: PASS')
"

echo ""
echo "=== All 5 smoke tests PASSED ==="
