#!/usr/bin/env python3
"""threadpoolctl consumer test (R34).

The upstream sdist ships **no test suite** (5 files only), so this consumer
test is the sole executable evidence.  It must therefore exercise the real
public API rather than merely importing the module:

  * ``threadpool_info()`` returns the documented list-of-dicts structure
    (each entry has the documented keys);
  * ``threadpool_limits(limits=1)`` is usable as a context manager and
    restores the previous state on exit (state save/restore path);
  * importing the **single module** from ``site-packages`` root works
    (a packaging mistake would place ``threadpoolctl.py`` in a subdirectory
    and this import would fail).
"""
import os
import subprocess
import sys

SMOKE_PY = r'''
import sys
sys.path[0:0] = __import__("os").environ["PYTHONPATH"].split(":")

import threadpoolctl

print("threadpoolctl", threadpoolctl.__version__)
assert threadpoolctl.__version__ == "3.7.0", threadpoolctl.__version__

# ---- 1) 单模块必须能从 site-packages 根导入 ----
assert threadpoolctl.__file__.endswith("threadpoolctl.py"), \
    threadpoolctl.__file__

# ---- 2) 真实调用 threadpool_info()：结构契约 ----
info = threadpoolctl.threadpool_info()
assert isinstance(info, list), type(info)
for entry in info:
    for key in ("user_api", "internal_api", "num_threads", "prefix"):
        assert key in entry, (key, sorted(entry))
print("OK: threadpool_info() -> %d pool(s): %s"
      % (len(info), [e.get("internal_api") for e in info]))

# ---- 3) 真实使用上下文管理器（状态保存/恢复路径）----
before = [e.get("num_threads") for e in threadpoolctl.threadpool_info()]
with threadpoolctl.threadpool_limits(limits=1):
    inside = [e.get("num_threads") for e in threadpoolctl.threadpool_info()]
    if before:
        assert all(n == 1 for n in inside), inside
after = [e.get("num_threads") for e in threadpoolctl.threadpool_info()]
if before:
    assert after == before, (before, after)
print("OK: threadpool_limits(limits=1) applied and restored: %s" % after)

print("OK: threadpoolctl single module + real API works")
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    site = os.path.join(pkg, "lib", "python3.12", "site-packages")
    # 单模块：必须在 site-packages 根
    mod = os.path.join(site, "threadpoolctl.py")
    if not os.path.isfile(mod):
        print(f"FAIL: threadpoolctl.py missing at site-packages root: {mod}",
              file=sys.stderr)
        return 1
    env = dict(os.environ)
    env["PYTHONPATH"] = site
    py = sys.executable
    r = subprocess.run([py, "-c", SMOKE_PY], capture_output=True,
                       text=True, env=env)
    if r.returncode != 0:
        print(f"FAIL: threadpoolctl API: {r.stderr}", file=sys.stderr)
        return 1
    print(r.stdout.strip())
    print("OK: threadpoolctl module + real API works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
