"""selftest — 一键冒烟测试入口（v12.6 L5）。

用法: ohc-run.py selftest
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


def selftest_cli(argv: list[str] | None = None) -> int:
    tests_dir = Path(__file__).resolve().parent.parent.parent / "tests"
    # v12.24: 显式加 scripts 与 tests 到 sys.path——discover 环境（非直跑）
    # 下 test_v1210 等模块的内部 sys.path 注入可能晚于 import，导致 ImportError
    for p in (str(tests_dir), str(tests_dir.parent / "scripts")):
        if p not in sys.path:
            sys.path.insert(0, p)
    loader = unittest.TestLoader()
    suite = loader.discover(str(tests_dir), pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1
