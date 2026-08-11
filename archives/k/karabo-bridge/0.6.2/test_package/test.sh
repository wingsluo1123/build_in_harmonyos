#!/usr/bin/env bash
# karabo-bridge 0.6.2 test_package smoke test
# R34 实质测试：实际 import karabo_bridge 并调用其公开 API
# （__version__、Client/ServerInThread 类、serialize/deserialize 真实往返），
# 而非 AST/文件存在性检查（PR 审查 P1 改正）。
#
# 说明：serialize/deserialize 无需真实 ZMQ IPC 连接即可验证（serializer.py
# 自带 Frame 哑对象，deserialize 接受 bytes 列表）；本机 Python 环境提供
# msgpack/msgpack_numpy/numpy 依赖。若目标环境缺 pyzmq 导致 import 失败，
# 本脚本会明确报错而非静默通过。

set -euo pipefail

echo "=== karabo-bridge 0.6.2 Smoke Test ==="

# Test 1: 实际 import + 版本断言
echo "--- Test 1: import + version ---"
python3 -c "
import karabo_bridge
print('karabo_bridge imported from:', karabo_bridge.__file__)
assert karabo_bridge.__version__ == '0.6.2', \
    f'Expected 0.6.2, got {karabo_bridge.__version__!r}'
print('Version assertion: PASS (', karabo_bridge.__version__, ')')
"

# Test 2: Client 类实际可用（导入并检查可实例化所需的类定义）
echo "--- Test 2: Client class ---"
python3 -c "
from karabo_bridge import Client
print('Client class:', Client)
assert Client is not None and isinstance(Client, type)
print('Client class assertion: PASS')
"

# Test 3: ServerInThread + Sender 类实际可用
echo "--- Test 3: ServerInThread + Sender classes ---"
python3 -c "
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
