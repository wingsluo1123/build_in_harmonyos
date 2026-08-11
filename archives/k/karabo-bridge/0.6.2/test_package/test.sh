#!/usr/bin/env bash
# karabo-bridge 0.6.2 test_package smoke test
# R34 实质测试：实际 import karabo_bridge 并调用其公开 API
# （__version__、Client/ServerInThread 类、serialize/deserialize 真实往返）。
#
# CI 沙箱无 pyzmq：karabo_bridge/__init__.py `from .client import *` 会
# `import zmq`（client.py:12），真实 import 在 CI 报 ModuleNotFoundError。
# 处理：测试 Python 代码先向 sys.modules 注入 mock zmq 模块（提供 Frame 类，
# serializer.py 自带 Frame 哑对象逻辑一致），再真实 import karabo_bridge，
# 真实调用 serialize/deserialize（无需真实 ZMQ IPC 连接即可往返验证）。

set -euo pipefail

echo "=== karabo-bridge 0.6.2 Smoke Test ==="

# Test 1: 实际 import + 版本断言（mock zmq 后）
echo "--- Test 1: import + version ---"
python3 -c "
import sys, types
zmq = types.ModuleType('zmq')
class Frame:
    def __init__(self, data): self.bytes = data; self.buffer = data
zmq.Frame = Frame
sys.modules['zmq'] = zmq
import karabo_bridge
print('karabo_bridge imported from:', karabo_bridge.__file__)
assert karabo_bridge.__version__ == '0.6.2', \
    f'Expected 0.6.2, got {karabo_bridge.__version__!r}'
print('Version assertion: PASS (', karabo_bridge.__version__, ')')
"

# Test 2: Client 类实际可用
echo "--- Test 2: Client class ---"
python3 -c "
import sys, types
zmq = types.ModuleType('zmq')
class Frame:
    def __init__(self, data): self.bytes = data; self.buffer = data
zmq.Frame = Frame
sys.modules['zmq'] = zmq
from karabo_bridge import Client
print('Client class:', Client)
assert Client is not None and isinstance(Client, type)
print('Client class assertion: PASS')
"

# Test 3: ServerInThread + Sender 类实际可用
echo "--- Test 3: ServerInThread + Sender classes ---"
python3 -c "
import sys, types
zmq = types.ModuleType('zmq')
class Frame:
    def __init__(self, data): self.bytes = data; self.buffer = data
zmq.Frame = Frame
sys.modules['zmq'] = zmq
from karabo_bridge import ServerInThread
from karabo_bridge.server import Sender
print('ServerInThread:', ServerInThread)
print('Sender:', Sender)
assert isinstance(ServerInThread, type) and isinstance(Sender, type)
print('ServerInThread/Sender assertion: PASS')
"

# Test 4: serialize 实际调用（真实数据 → 消息）
echo "--- Test 4: serialize() real call ---"
python3 -c "
import sys, types
zmq = types.ModuleType('zmq')
class Frame:
    def __init__(self, data): self.bytes = data; self.buffer = data
zmq.Frame = Frame
sys.modules['zmq'] = zmq
from karabo_bridge import serialize
data = {'SRC': {'value': 42}}
meta = {'SRC': {'timestamp.tid': 123, 'timestamp.sec': '123'}}
msg = serialize(data, metadata=meta)
assert isinstance(msg, list) and len(msg) == 2, f'unexpected msg: {msg!r}'
assert len(msg[0]) > 0 and len(msg[1]) > 0
print('serialize() real call: PASS (', len(msg), 'parts )')
"

# Test 5: serialize/deserialize 真实往返（标量 + numpy 数组）
echo "--- Test 5: serialize/deserialize round-trip ---"
python3 -c "
import sys, types
zmq = types.ModuleType('zmq')
class Frame:
    def __init__(self, data): self.bytes = data; self.buffer = data
zmq.Frame = Frame
sys.modules['zmq'] = zmq
import numpy as np
from karabo_bridge import serialize, deserialize
data = {'SRC': {'value': 42, 'arr': np.array([1.0, 2.0, 3.0])}}
meta = {'SRC': {'timestamp.tid': 123, 'timestamp.sec': '123'}}
msg = serialize(data, metadata=meta)
back, back_meta = deserialize(msg)
assert back['SRC']['value'] == 42, f'value roundtrip failed: {back!r}'
assert np.allclose(back['SRC']['arr'], [1.0, 2.0, 3.0]), 'array roundtrip failed'
assert back_meta['SRC']['timestamp.tid'] == 123, 'metadata roundtrip failed'
print('serialize/deserialize round-trip: PASS (scalar + numpy array)')
"

echo ""
echo "=== All 5 smoke tests PASSED (real API calls) ==="
