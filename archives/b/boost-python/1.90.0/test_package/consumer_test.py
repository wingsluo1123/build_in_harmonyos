#!/usr/bin/env python3
"""Consumer test: import the built Boost.Python extension and assert results."""
import os
import sys

# test() 的 cwd 为 build folder，test_ext.so 由 CMake 输出到 build folder 根
sys.path.insert(0, os.getcwd())

import test_ext

assert test_ext.add(2, 3) == 5, "add(2,3) != 5"
assert test_ext.add(-1, 1) == 0, "add(-1,1) != 0"
assert test_ext.greet() == "hello-from-boost-python", "greet() mismatch"

print("CONSUMER_TEST_OK: add(2,3)=5, add(-1,1)=0, greet='hello-from-boost-python'")
print("ALL_ASSERTIONS_PASSED (3 asserts)")
