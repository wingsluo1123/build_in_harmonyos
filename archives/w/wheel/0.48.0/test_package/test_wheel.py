#!/usr/bin/env python3
"""wheel 消费侧测试：验证**从制品**能 import 到 wheel，且关键能力可用。

重点覆盖 meson-python 上游套件实际用到的入口 `wheel.wheelfile`——本位正是为它
而加（见 notes.md：该套件 6 个模块 import wheel.wheelfile，此前因缺 wheel 在
pytest 采集期失败）。
"""
import os
import sys

failures = 0


def check(cond, msg):
    global failures
    if cond:
        print("PASS: %s" % msg)
    else:
        print("FAIL: %s" % msg)
        failures += 1


def main():
    if len(sys.argv) < 2:
        print("FAIL: missing package folder argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    site = os.path.join(pkg, "lib", "python3.12", "site-packages")
    mod = os.path.join(site, "wheel", "__init__.py")
    if not os.path.isfile(mod):
        print("FAIL: wheel package missing: %s" % mod, file=sys.stderr)
        return 1
    sys.path.insert(0, site)

    import wheel
    check(wheel.__version__ == "0.48.0", "wheel.__version__ == 0.48.0（实得 %s）"
          % getattr(wheel, "__version__", None))

    # meson-python 上游套件实际 import 的入口
    import wheel.wheelfile as wf
    check(hasattr(wf, "WheelFile"), "wheel.wheelfile.WheelFile 存在")
    check(isinstance(wf.WheelFile, type), "WheelFile 是一个类")
    for attr in ("writestr", "close", "read"):
        check(hasattr(wf.WheelFile, attr),
              "WheelFile.%s 可用（写/读 .whl 的关键方法）" % attr)

    # 其余按**制品实际内容**断言（教训：`wheel.tags` 在 0.48.0 里并不存在，
    # 初版按过时印象写了它，实测 ModuleNotFoundError → 这里只断言查证过的符号）
    # bdist_wheel 组件 import setuptools（0.48.0 的 bdist_wheel.py/_bdist_wheel.py）。
    # CI 的 hnp python 无 setuptools → 按异常分类：缺的是 setuptools = 环境缺口，
    # 如实 SKIP 不计失败；缺的是 wheel 自身模块仍算 FAIL（防分类器洗白真缺陷）。
    try:
        import wheel.bdist_wheel as bw
    except ModuleNotFoundError as exc:
        if (exc.name or "").split(".")[0] == "setuptools":
            print("SKIP: wheel.bdist_wheel needs setuptools (%r) — 测试环境无 "
                  "setuptools，不计失败（meson-python 套件用的入口是 wheelfile）"
                  % exc.name)
        else:
            raise
    else:
        check(hasattr(bw, "bdist_wheel"), "wheel.bdist_wheel.bdist_wheel 存在")
    check(wf.__all__ == ["WHEEL_INFO_RE", "WheelFile", "WheelError"],
          "wheel.wheelfile.__all__ 与制品一致：%r" % (wf.__all__,))
    check(issubclass(wf.WheelError, Exception),
          "wheel.wheelfile.WheelError 是异常类")
    check(wf.WHEEL_INFO_RE.__class__.__name__ == "Pattern",
          "wheel.wheelfile.WHEEL_INFO_RE 是已编译正则")

    print("assertions failed: %d" % failures)
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
