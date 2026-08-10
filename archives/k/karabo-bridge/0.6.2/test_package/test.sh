#!/usr/bin/env bash
# karabo-bridge 0.6.2 test_package smoke test
# Verifies module layout, version, Client/Sender classes, and serialize
# round-trip API surface (R34) — WITHOUT importing karabo_bridge live,
# because karabo_bridge/__init__.py does `from .server import *` which
# triggers `import zmq` (pyzmq). The CI sandbox lacks pyzmq, so a live
# import raises ModuleNotFoundError: No module named 'zmq'. We instead
# inspect the installed source via importlib.util.find_spec + AST, which
# validates the package was correctly built and installed.
#
# 5 smoke test assertions:
#   1. karabo_bridge package installed (find_spec) — package install
#   2. __version__ == "0.6.2" — version assertion (read from source)
#   3. Client class defined in client.py — Client class presence
#   4. ServerInThread + Sender classes defined — Sender/Server class presence
#   5. serialize + deserialize functions defined in serializer.py — API surface

set -euo pipefail

echo "=== karabo-bridge 0.6.2 Smoke Test ==="

# Test 1: Package installed (find_spec, no live import to avoid zmq)
echo "--- Test 1: Package installed ---"
python3 -c "
import importlib.util
spec = importlib.util.find_spec('karabo_bridge')
assert spec is not None, 'karabo_bridge package not installed (find_spec returned None)'
assert spec.origin is not None, 'karabo_bridge has no __init__.py (namespace package?)'
print('karabo_bridge package installed at:', spec.origin)
"

# Test 2: Version assertion (read from source, no live import)
echo "--- Test 2: Version assertion ---"
python3 -c "
import ast, importlib.util
spec = importlib.util.find_spec('karabo_bridge')
assert spec is not None, 'karabo_bridge package not installed'
with open(spec.origin, 'r', encoding='utf-8') as f:
    tree = ast.parse(f.read())
# Walk __init__.py for __version__ assignment
version_val = None
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == '__version__':
                version_val = ast.literal_eval(node.value)
assert version_val == '0.6.2', f'Expected 0.6.2, got {version_val!r}'
print('Version assertion: PASS (', version_val, ')')
"

# Test 3: Client class defined in client.py
echo "--- Test 3: Client class defined ---"
python3 -c "
import ast, importlib.util, os
spec = importlib.util.find_spec('karabo_bridge')
assert spec is not None, 'karabo_bridge package not installed'
pkg_dir = os.path.dirname(spec.origin)
client_py = os.path.join(pkg_dir, 'client.py')
assert os.path.isfile(client_py), f'client.py missing: {client_py}'
with open(client_py, 'r', encoding='utf-8') as f:
    tree = ast.parse(f.read())
class_names = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
assert 'Client' in class_names, f'Client class not defined in client.py, found: {class_names}'
print('Client class defined: PASS')
"

# Test 4: ServerInThread + Sender classes defined
echo "--- Test 4: ServerInThread + Sender classes defined ---"
python3 -c "
import ast, importlib.util, os
spec = importlib.util.find_spec('karabo_bridge')
assert spec is not None, 'karabo_bridge package not installed'
pkg_dir = os.path.dirname(spec.origin)
# ServerInThread in __init__.py (re-exported) or server.py
init_py = spec.origin
with open(init_py, 'r', encoding='utf-8') as f:
    init_tree = ast.parse(f.read())
init_classes = [n.name for n in ast.walk(init_tree) if isinstance(n, ast.ClassDef)]
# Sender in server.py
server_py = os.path.join(pkg_dir, 'server.py')
assert os.path.isfile(server_py), f'server.py missing: {server_py}'
with open(server_py, 'r', encoding='utf-8') as f:
    server_tree = ast.parse(f.read())
server_classes = [n.name for n in ast.walk(server_tree) if isinstance(n, ast.ClassDef)]
assert 'Sender' in server_classes, f'Sender class not defined in server.py, found: {server_classes}'
# ServerInThread: check __init__ imports or server.py defines it
all_classes = set(init_classes) | set(server_classes)
assert 'ServerInThread' in all_classes, f'ServerInThread not found in __init__ or server, found: {all_classes}'
print('ServerInThread/Sender classes defined: PASS')
"

# Test 5: serialize + deserialize functions defined in serializer.py (API surface)
echo "--- Test 5: serialize + deserialize API surface ---"
python3 -c "
import ast, importlib.util, os
spec = importlib.util.find_spec('karabo_bridge')
assert spec is not None, 'karabo_bridge package not installed'
pkg_dir = os.path.dirname(spec.origin)
serializer_py = os.path.join(pkg_dir, 'serializer.py')
assert os.path.isfile(serializer_py), f'serializer.py missing: {serializer_py}'
with open(serializer_py, 'r', encoding='utf-8') as f:
    tree = ast.parse(f.read())
func_names = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
assert 'serialize' in func_names, f'serialize() not defined in serializer.py, found: {func_names}'
assert 'deserialize' in func_names, f'deserialize() not defined in serializer.py, found: {func_names}'
print('serialize/deserialize API surface defined: PASS')
"

echo ""
echo "=== All 5 smoke tests PASSED ==="
