#!/usr/bin/env python3
"""joblib consumer test (R34): package importable from the packaged
site-packages + real memory-caching and parallel execution (not an
import-only smoke test).

The inner script exercises joblib's two core features for real:
  * ``Memory.cache`` — a function is cached to disk and the cached result is
    replayed on the second call (func hashing / disk store path);
  * ``Parallel`` — a real workload is spread over loky worker processes and
    the results are checked (process pool / pickling path).

Because the two features above are precisely what scikit-learn relies on,
a broken or empty package cannot pass.
"""
import os
import subprocess
import sys

SMOKE_PY = r'''
import os
import sys
import tempfile

# 追加而非覆盖：joblib 运行期要 import cloudpickle（由 runenv 注入），
# 覆盖 PYTHONPATH 会把它丢掉 → ModuleNotFoundError。
sys.path[0:0] = [p for p in os.environ.get("PYTHONPATH", "").split(os.pathsep) if p]

import joblib
from joblib import Memory, Parallel, delayed

print("joblib", joblib.__version__)
assert joblib.__version__ == "1.6.0", joblib.__version__

# ---- 1) 真实磁盘缓存：第二次调用必须命中缓存 ----
with tempfile.TemporaryDirectory(prefix="jb-cache-") as tdc:
    memory = Memory(location=tdc, verbose=0)

    calls = {"n": 0}

    @memory.cache
    def slow_double(x):
        calls["n"] += 1
        return x * 2

    assert slow_double(21) == 42
    assert slow_double(21) == 42
    assert calls["n"] == 1, "cache miss: function re-executed %d times" % calls["n"]
    # 磁盘上确实落了缓存目录
    assert os.path.isdir(os.path.join(tdc, "joblib")), os.listdir(tdc)
    print("OK: Memory.cache replayed the cached result (1 real call)")

# ---- 2) 真实并行执行（loky 进程池）----
results = Parallel(n_jobs=2)(delayed(abs)(-i) for i in range(8))
assert results == [0, 1, 2, 3, 4, 5, 6, 7], results
print("OK: Parallel(n_jobs=2) computed", results)

print("OK: joblib caching + parallel execution work")
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    site = os.path.join(pkg, "lib", "python3.12", "site-packages")
    mod = os.path.join(site, "joblib", "__init__.py")
    if not os.path.isfile(mod):
        print(f"FAIL: joblib module missing: {mod}", file=sys.stderr)
        return 1
    env = dict(os.environ)
    # 追加而非覆盖：conanrun 里 joblib 的 runenv_info 已经带上了 cloudpickle
    # 的 site-packages，覆盖会把 joblib 的硬依赖丢掉 → joblib 导入期
    # `from cloudpickle import dumps, loads` 直接 ModuleNotFoundError。
    env["PYTHONPATH"] = site + os.pathsep + env.get("PYTHONPATH", "")
    py = sys.executable
    r = subprocess.run([py, "-c", SMOKE_PY], capture_output=True,
                       text=True, env=env)
    if r.returncode != 0:
        print(f"FAIL: joblib API: {r.stderr}", file=sys.stderr)
        print(f"[joblib] PYTHONPATH={env['PYTHONPATH']}", file=sys.stderr)
        return 1
    print(r.stdout.strip())
    print("OK: joblib module + real cache/parallel works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
