#!/usr/bin/env python3
"""Consumer test: import the built Boost.Python extension and assert results.

test() 将本脚本复制到本轮 TMPDIR 运行目录后执行；PYTHONPATH 首位为运行目录，
因此 import test_ext 必须解析到运行目录中的暂存模块（输出 __file__ 佐证）。

除 3 项功能断言外，本脚本还通过 /proc/self/maps 取证实际动态加载路径：
test_ext.so 与 libboost_python312.so 必须都映射自本轮创建的 boostpy-run-* TMPDIR
运行目录（按目录 basename 判定，容忍 HMDFS 挂载双视图路径）。
"""
import ctypes
import os
import sys

print("sys.executable =", sys.executable)

# test() 的 cwd 为 TMPDIR 运行目录，PYTHONPATH 首位亦为运行目录
sys.path.insert(0, os.getcwd())
run_dir = os.path.realpath(os.getcwd())
run_name = os.path.basename(run_dir)

# conanrun 环境可能把 conan 缓存 lib 目录放在 LD_LIBRARY_PATH 前面，导致
# NEEDED 解析命中包内原件而非运行目录副本。import 前强制运行目录副本优先。
os.environ["LD_LIBRARY_PATH"] = (
    run_dir + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
)
# 以绝对路径预加载运行目录中的 libboost_python312.so（RTLD_GLOBAL），
# 保证 dlopen(test_ext.so) 解析 NEEDED 时命中运行目录副本。
ctypes.CDLL(os.path.join(run_dir, "libboost_python312.so"), mode=ctypes.RTLD_GLOBAL)

import test_ext

print("test_ext.__file__ =", test_ext.__file__)

assert test_ext.add(2, 3) == 5, "add(2,3) != 5"
assert test_ext.add(-1, 1) == 0, "add(-1,1) != 0"
assert test_ext.greet() == "hello-from-boost-python", "greet() mismatch"


def _real_map_paths():
    """返回 {basename: 路径列表} 的实际映射路径（/proc/self/maps 优先）。"""
    mapped = {}
    maps = "/proc/self/maps"
    if os.path.exists(maps):
        with open(maps) as f:
            for line in f:
                for name in ("test_ext.so", "libboost_python312.so"):
                    if name in line:
                        path = line.split()[-1]
                        if path.startswith("/"):
                            mapped.setdefault(name, []).append(path)
    return mapped


mapped = _real_map_paths()
print("mapped test_ext.so =", mapped.get("test_ext.so"))
print("mapped libboost_python312.so =", mapped.get("libboost_python312.so"))
for name in ("test_ext.so", "libboost_python312.so"):
    paths = mapped.get(name) or []
    assert paths, "{} not found in real runtime mapping".format(name)
    # 至少一个映射来自本轮 boostpy-run-* 运行目录（按目录 basename 判定，
    # 容忍 HMDFS 双视图：/storage/Users/currentUser/... 与
    # /data/service/el2/100/hmdfs/account/files/Docs/... 指向同一目录）
    from_tmpdir = [
        p
        for p in paths
        if os.path.basename(os.path.dirname(p)) == run_name
        and "boostpy-run-" in os.path.dirname(p)
    ]
    assert from_tmpdir, "{} has no mapping from run_dir {}".format(name, paths)

print("CONSUMER_TEST_OK: add(2,3)=5, add(-1,1)=0, greet='hello-from-boost-python'")
print("ALL_ASSERTIONS_PASSED (3 asserts + 2 real mapping asserts)")
