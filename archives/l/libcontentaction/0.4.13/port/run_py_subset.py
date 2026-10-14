#!/usr/bin/env python3
"""run_py_subset.py —— 按方法执行上游 unittest 用例（不改动上游测试文件）。

上游 test-mimes.py 等文件把 DBus 依赖方法与纯查询/Exec 方法写在同一个
TestCase 里。本驱动按方法名抽取执行上游**原始断言**，用于在不具备
python-dbus 的执行环境里真实执行其中不依赖 DBus 的方法（其余方法由
run_py_case.sh 在依赖齐备时全量执行）。

用法: python3 run_py_subset.py <test-file.py> <Class.method> [<Class.method> ...]
"""
import importlib.util
import sys
import unittest


def main():
    if len(sys.argv) < 3:
        print("usage: run_py_subset.py <test-file.py> <Class.method> [...]")
        return 2
    path = sys.argv[1]
    names = sys.argv[2:]

    spec = importlib.util.spec_from_file_location("lca_upstream_case", path)
    # spec/loader 可能为 None（路径缺失或不可读）：显式报错并返回 2，
    # 避免下层抛 AttributeError 掩盖真实原因与预期退出码。
    if spec is None or spec.loader is None:
        print("run_py_subset.py: cannot load upstream case module: %s" % path, file=sys.stderr)
        return 2
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for name in names:
        if "." not in name:
            print("run_py_subset.py: bad method spec (expected Class.method): %s" % name,
                  file=sys.stderr)
            return 2
        cls_name, method = name.rsplit(".", 1)
        if not hasattr(module, cls_name):
            # 与上面的 spec/'.' 校验同款：显式诊断 + 返回 2（用法错误），
            # 不抛未捕获 AttributeError 破坏退出码语义。
            print("run_py_subset.py: class not found in upstream module: %s" % cls_name,
                  file=sys.stderr)
            return 2
        cls = getattr(module, cls_name)
        if not hasattr(cls, method):
            # 与上面的 class-not-found 分支同款：方法名拼错时显式诊断 + 返回 2（用法错误）。
            # 否则 loadTestsFromNames 会抛 ValueError 逃逸 main()，打出 traceback 并以
            # exit 1 结束，与真实断言失败无法区分，也违背本文件“用法错误返回 2”的约定。
            print("run_py_subset.py: method not found on %s: %s" % (cls_name, method),
                  file=sys.stderr)
            return 2
        suite.addTest(loader.loadTestsFromNames([method], cls))

    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print("SUBSET RESULT: %d run, %d failures, %d errors"
          % (result.testsRun, len(result.failures), len(result.errors)))
    # 空套件/部分解析会被 wasSuccessful() 判为"成功"，故显式校验实际执行用例数，
    # 杜绝"没跑到任何用例"被记为通过。
    if result.testsRun != len(names):
        print("SUBSET FAIL: expected %d tests, ran %d" % (len(names), result.testsRun),
              file=sys.stderr)
        return 1
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
