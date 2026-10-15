#!/usr/bin/env python3
"""消费测试 — propka 3.5.1 真实产物校验（全部离线，不触网）。

用法: python3 check_propka.py <package_folder>
"""
import os
import sys

checks = fails = 0

# 关键文件（propka 3.5.1 实测的模块名；注意**没有** propka/protein.py）
NEED = ("__init__.py", "atom.py", "molecular_container.py", "run.py",
        "hybrid36.py", "group.py", "calculations.py", "_version.py")
# 实测可导入的子模块
SUBMODULES = ("propka.molecular_container", "propka.atom", "propka.group",
              "propka.run", "propka.hybrid36")


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
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    pkg = sys.argv[1]

    mod = None
    for root, _dirs, _files in os.walk(os.path.join(pkg, "lib")):
        if os.path.basename(root) == "propka":
            mod = root
            break
    if not mod or not os.path.isdir(mod):
        fail("产物缺失：site-packages 下找不到 propka/ 模块目录")
        print("\nchecks=%d fails=%d\nRESULT: FAIL" % (checks, fails))
        return 1
    ok("产物齐备：propka 模块位于 %s" % os.path.relpath(mod, pkg))

    miss = [n for n in NEED if not os.path.exists(os.path.join(mod, n))]
    if miss:
        fail("关键文件缺失：%s" % miss)
    else:
        ok("关键文件齐备：%s" % " / ".join(NEED))

    sys.path.insert(0, os.path.dirname(mod))
    try:
        import propka
        ok("import propka 成功（零运行期依赖；包内模块不 import numpy）")
    except Exception as exc:
        fail("import propka 失败：%s" % str(exc)[:160])
        print("\nchecks=%d fails=%d\nRESULT: FAIL" % (checks, fails))
        return 1

    ver = getattr(propka, "__version__", None)
    if ver == "3.5.1":
        ok("__version__ == '3.5.1'（与包版本一致）")
    else:
        fail("__version__ 期望 '3.5.1'，实际 %r" % ver)

    # 真实离线功能：PDB hybrid-36 标识符解码（纯函数，无文件/网络）
    try:
        from propka import hybrid36
        got = hybrid36.decode("A0000")
        if got == 100000:
            ok("真实离线功能：hybrid36.decode('A0000') == 100000（PDB hybrid-36 解码正确）")
        else:
            fail("hybrid36.decode('A0000') 期望 100000，实际 %r" % got)
    except Exception as exc:
        fail("propka.hybrid36.decode 调用失败：%s" % str(exc)[:160])

    # 子模块面（按实测模块名，不臆造）
    missed = []
    for name in SUBMODULES:
        try:
            __import__(name)
        except Exception as exc:
            missed.append("%s(%s)" % (name, str(exc)[:40]))
    if missed:
        fail("子模块导入失败：%s" % missed)
    else:
        ok("子模块面齐备：%s 全部可导入" % " / ".join(SUBMODULES))

    total = 0
    for root, _dirs, files in os.walk(mod):
        total += sum(os.path.getsize(os.path.join(root, f)) for f in files)
    n_py = sum(1 for _r, _d, fs in os.walk(mod) for f in fs if f.endswith(".py"))
    ok("证据：propka 模块总字节 %d（%d 个 .py）；python %s"
       % (total, n_py, sys.version.split()[0]))

    print("\nchecks=%d fails=%d" % (checks, fails))
    print("RESULT: %s" % ("PASS" if fails == 0 else "FAIL"))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
