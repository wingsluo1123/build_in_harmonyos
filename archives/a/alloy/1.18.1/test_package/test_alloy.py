#!/usr/bin/env python3
"""alloy 1.18.1 consumer smoke test (R34)."""

import os
import subprocess
import sys
import tempfile

exe = sys.argv[1]
passed = True


def run(args, timeout=90):
    return subprocess.run([exe] + args, capture_output=True, text=True,
                          timeout=timeout)


# Test 1: --version 输出含 v1.18.1
r = run(["--version"])
ok = r.returncode == 0 and "1.18.1" in (r.stdout + r.stderr)
passed &= ok
print(("PASS" if ok else "FAIL") +
      f": alloy --version -> {(r.stdout + r.stderr).strip()[:60]}")

# Test 2: --version 与 -version 等价（cobra 版本旗标）
r = run(["-version"])
ok = r.returncode == 0 and "1.18.1" in (r.stdout + r.stderr)
passed &= ok
print(("PASS" if ok else "FAIL") + ": alloy -version -> version string")

# Test 3: alloy fmt 解析最小配置（Alloy 配置语言解析器）
cfg = 'logging {\n\tlevel = "info"\n}\n'
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "config.alloy")
    with open(p, "w") as f:
        f.write(cfg)
    r = run(["fmt", p])
    ok = r.returncode == 0
    passed &= ok
    print(("PASS" if ok else "FAIL") +
          f": alloy fmt minimal config rc={r.returncode}")

print("RESULT:", "ALL PASS" if passed else "FAILED")
sys.exit(0 if passed else 1)
