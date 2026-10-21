#!/usr/bin/env python3
"""上游接口功能测试：驱动 dual-function-keys 的 -c + stdin/stdout 协议。

用法: test_dfk.py <bin_dir> <cfg.yaml>

断言集（覆盖上游全部对外行为面）：
  T01 tap（TAP_MILLISEC 内按下并松开）合成 TAP 键
  T02 hold（超 TAP_MILLISEC 松开）保留 HOLD 键、不合成 TAP
  T03 未映射按键原样透传
  T04 非按键事件（EV_REL）原样透传
  T05 -v 输出版本号且退出码 0
  T06 缺 -c 时打印 usage 且退出码 1

注意：上游无自动化测试（无 tests/、无 make test/ctest/pytest 入口），
本脚本基于上游 man page/README 文档化的行为编写的消费者侧验证。
"""
import os
import struct
import subprocess
import sys

BIN = os.path.join(sys.argv[1], "dual-function-keys")
CFG = sys.argv[2]

EV_KEY = 1
EV_REL = 2
KEY_LEFTSHIFT = 42
KEY_DELETE = 111
KEY_A = 30
REL_X = 0

NAMES = {KEY_LEFTSHIFT: "LEFTSHIFT", KEY_DELETE: "DELETE", KEY_A: "A"}


def ev(sec, usec, type_, code, value):
    # struct input_event (aarch64 / musl, LP64): timeval(2x8) + u16 + u16 + s32
    return struct.pack("<qqHHi", sec, usec, type_, code, value)


def run(events):
    p = subprocess.run([BIN, "-c", CFG], input=b"".join(events),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert len(p.stdout) % 24 == 0, "stdout not aligned to input_event records"
    out = []
    for i in range(0, len(p.stdout), 24):
        _s, _u, t, c, v = struct.unpack("<qqHHi", p.stdout[i:i + 24])
        out.append((t, c, v))
    return out, p


def key_events(out):
    return [(NAMES.get(c, str(c)), v) for (t, c, v) in out if t == EV_KEY]


results = []


def check(name, cond, detail):
    results.append(cond)
    print(("PASS " if cond else "FAIL ") + name + " :: " + detail)


# T01 tap -> TAP key synthesized
out, _ = run([ev(0, 0, EV_KEY, KEY_LEFTSHIFT, 1),
              ev(0, 50_000, EV_KEY, KEY_LEFTSHIFT, 0)])
ke = key_events(out)
exp = [("LEFTSHIFT", 1), ("LEFTSHIFT", 0), ("DELETE", 1), ("DELETE", 0)]
check("T01_tap_synthesizes_tap_key", ke == exp, f"expect={exp} got={ke}")

# T02 hold -> HOLD key kept, no TAP synthesis
out, _ = run([ev(0, 0, EV_KEY, KEY_LEFTSHIFT, 1),
              ev(0, 500_000, EV_KEY, KEY_LEFTSHIFT, 0)])
ke = key_events(out)
exp = [("LEFTSHIFT", 1), ("LEFTSHIFT", 0)]
check("T02_hold_keeps_hold_key", ke == exp, f"expect={exp} got={ke}")

# T03 unmapped key forwarded untouched
out, _ = run([ev(0, 0, EV_KEY, KEY_A, 1), ev(0, 50_000, EV_KEY, KEY_A, 0)])
ke = key_events(out)
exp = [("A", 1), ("A", 0)]
check("T03_unmapped_key_forwarded", ke == exp, f"expect={exp} got={ke}")

# T04 non-key events (EV_REL) forwarded untouched
out, _ = run([ev(0, 0, EV_REL, REL_X, 5), ev(0, 10_000, EV_KEY, KEY_A, 1),
              ev(0, 20_000, EV_KEY, KEY_A, 0)])
ke = key_events(out)
exp = [("A", 1), ("A", 0)]
rel = [1 for (t, c, v) in out if t == EV_REL]
check("T04_rel_event_forwarded", ke == exp and len(rel) == 1,
      f"expect={exp} got={ke} rel={len(rel)}")

# T05 -v prints version, exit 0
v = subprocess.run([BIN, "-v"], stdout=subprocess.PIPE)
check("T05_version_flag", b"1.5.0" in v.stdout and v.returncode == 0,
      f"got={v.stdout!r} rc={v.returncode}")

# T06 missing -c -> usage on stderr, exit 1
m = subprocess.run([BIN], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
check("T06_missing_config_exit1",
      m.returncode == 1 and b"usage:" in m.stderr, f"rc={m.returncode}")

passed = sum(1 for c in results if c)
print(f"\nRESULT: {passed}/{len(results)} passed")
sys.exit(0 if passed == len(results) else 1)
