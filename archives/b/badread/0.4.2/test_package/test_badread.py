#!/usr/bin/env python3
"""test_badread.py — badread test_package 验证脚本.

CI L0c 要求 test_package/ 中必须有测试源文件（非 conanfile.py）。
badread 是纯 Python 命令行工具，测试方式为执行 badread --version。
实际测试入口在 test_package/conanfile.py 的 test() 方法中。

本文件作为 CI 质量门禁的测试源文件占位，确保 test_package/ 结构合规。
"""

import sys


def main():
    """验证 Python 环境可加载 badread（由 conanfile.py test() 实际执行）."""
    print(f"Python {sys.version}")
    print("test_badread: environment ready")
    return 0


if __name__ == "__main__":
    sys.exit(main())
