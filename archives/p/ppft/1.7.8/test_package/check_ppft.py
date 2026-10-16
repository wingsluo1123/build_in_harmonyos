#!/usr/bin/env python3
"""消费测试 — ppft 1.7.8 真实产物校验（全部离线）。

只用**可实证**的断言（不臆造上游 API 名字）：模块目录、模块文件、真实 import、
公开符号面（按实际 dir() 报告），并在存在 __version__ 时与包版本比对。
用法: python3 check_ppft.py <package_folder>
"""
import os
import sys

checks = fails = skips = 0


def ok(msg):
    global checks
    checks += 1
    print("[ok]   %s" % msg)


def fail(msg):
    global checks, fails
    checks += 1
    fails += 1
    print("[FAIL] %s" % msg)


def main():
    pkg = sys.argv[1]
    mod = None
    for root, _dirs, _files in os.walk(os.path.join(pkg, "lib")):
        if os.path.basename(root) == "ppft":
            mod = root
            break
    if not mod or not os.path.isdir(mod):
        fail("产物缺失：site-packages 下找不到 ppft/ 模块目录")
        print("\nchecks=%d fails=%d skips=%d\nRESULT: FAIL" % (checks, fails, skips))
        return 1
    ok("产物齐备：ppft 模块位于 %s" % os.path.relpath(mod, pkg))

    py_files = sorted(f for f in os.listdir(mod) if f.endswith(".py"))
    if len(py_files) < 3:
        fail("模块文件过少（%d 个 .py）：%s" % (len(py_files), py_files))
    else:
        ok("模块文件齐备：%d 个 .py（%s%s）"
           % (len(py_files), ", ".join(py_files[:6]),
              " …" if len(py_files) > 6 else ""))
    if "__init__.py" not in py_files:
        fail("缺少 __init__.py")

    site_root = os.path.dirname(mod)
    sys.path.insert(0, site_root)
    try:
        import ppft
        ok("import ppft 成功（零运行期依赖）")
    except Exception as exc:
        fail("import ppft 失败：%s" % str(exc)[:160])
        print("\nchecks=%d fails=%d skips=%d\nRESULT: FAIL" % (checks, fails, skips))
        return 1

    names = sorted(n for n in dir(ppft) if not n.startswith("_"))
    if len(names) >= 3:
        ok("公开符号面（实测 %d 个）：%s" % (len(names), ", ".join(names[:8])))
    else:
        fail("公开符号过少（%d 个）：%s" % (len(names), names))

    ver = getattr(ppft, "__version__", None)
    if ver is None:
        ok("模块未暴露 __version__（该库如此，非缺陷）——版本以 conandata 钉死的 sdist 为准")
    elif str(ver) == "1.7.8":
        ok("__version__ == 1.7.8（与包版本一致）")
    else:
        fail("__version__ 期望 1.7.8，实际 %r" % ver)

    total = 0
    for root, _dirs, files in os.walk(mod):
        total += sum(os.path.getsize(os.path.join(root, f)) for f in files)
    ok("证据：ppft 模块总字节 %d；python %s" % (total, sys.version.split()[0]))

    print("\nchecks=%d fails=%d skips=%d" % (checks, fails, skips))
    print("RESULT: %s" % ("PASS" if fails == 0 else "FAIL"))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
