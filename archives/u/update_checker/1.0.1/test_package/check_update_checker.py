#!/usr/bin/env python3
"""消费测试 — update_checker 1.0.1 真实产物校验（全部离线，不触网）。

用法: python3 check_update_checker.py <package_folder>

说明：本库的联网能力（query_pypi / update_check）都需要真实外网与缓存目录，
消费者校验**只做离线可实证**的部分：模块/导入/公开符号面 + 三个纯函数
（parse_version / pretty_date / standard_release）+ UpdateChecker 构造 + 证据。
"""
import os
import sys
from datetime import datetime, timedelta, timezone

checks = fails = 0

NEED = ("__init__.py", "core.py", "py.typed")
# 上游 __all__ 的 12 个导出（1.0.1 实测）
EXPORTS = ("UpdateChecker", "UpdateResult", "__version__", "async_cache_results",
           "async_query_pypi", "async_update_check", "cache_results",
           "parse_version", "pretty_date", "query_pypi", "standard_release",
           "update_check")


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
        if os.path.basename(root) == "update_checker":
            mod = root
            break
    if not mod or not os.path.isdir(mod):
        fail("产物缺失：site-packages 下找不到 update_checker/ 模块目录")
        print("\nchecks=%d fails=%d\nRESULT: FAIL" % (checks, fails))
        return 1
    ok("产物齐备：update_checker 模块位于 %s" % os.path.relpath(mod, pkg))

    miss = [n for n in NEED if not os.path.exists(os.path.join(mod, n))]
    if miss:
        fail("关键文件缺失：%s" % miss)
    else:
        ok("模块文件齐备：%s（含 PEP 561 的 py.typed）" % " / ".join(NEED))

    sys.path.insert(0, os.path.dirname(mod))
    try:
        import update_checker as uc
        ok("import update_checker 成功（零运行期依赖）")
    except Exception as exc:
        fail("import update_checker 失败：%s" % str(exc)[:160])
        print("\nchecks=%d fails=%d\nRESULT: FAIL" % (checks, fails))
        return 1

    missing = [n for n in EXPORTS if not hasattr(uc, n)]
    if missing:
        fail("公开符号面缺项：%s" % missing)
    else:
        ok("公开符号面齐备：__all__ 的 %d 个导出全部可访问" % len(EXPORTS))

    # 真实离线 API 1：parse_version（纯函数，上游版本号归一化）
    try:
        a = uc.parse_version("1.2.3")
        b = uc.parse_version("1.0.0b1")
        if a == ("00000001", "00000002", "00000003", "*final") and \
           b == ("00000001", "*b", "00000001", "*final"):
            ok("真实离线 API：parse_version() 归一化正确（'1.2.3' 与 '1.0.0b1' 两例）")
        else:
            fail("parse_version() 结果不符：%r / %r" % (a, b))
    except Exception as exc:
        fail("parse_version() 调用失败：%s" % str(exc)[:160])

    # 真实离线 API 2：pretty_date（纯函数，人类可读时间差）
    try:
        now = datetime.now(timezone.utc)
        d2 = uc.pretty_date(now - timedelta(days=2))
        h1 = uc.pretty_date(now - timedelta(hours=1))
        if d2 == "2 days ago" and h1 == "1 hour ago":
            ok("真实离线 API：pretty_date() 正确（now-2d → '2 days ago'，now-1h → '1 hour ago'）")
        else:
            fail("pretty_date() 结果不符：%r / %r" % (d2, h1))
    except Exception as exc:
        fail("pretty_date() 调用失败：%s" % str(exc)[:160])

    # 真实离线 API 3：standard_release + UpdateChecker 构造（不联网）
    try:
        sr = uc.standard_release("1.0.0")
        checker = uc.UpdateChecker(bypass_cache=True)
        if sr is True and checker is not None:
            ok("真实离线 API：standard_release('1.0.0') is True；UpdateChecker(bypass_cache=True) 构造成功")
        else:
            fail("standard_release/UpdateChecker 结果不符：%r / %r" % (sr, checker))
    except Exception as exc:
        fail("standard_release/UpdateChecker 调用失败：%s" % str(exc)[:160])

    ver = getattr(uc, "__version__", None)
    if ver == "unknown":
        ok("__version__ == 'unknown'：上游 core.py 的兜底值（其版本由构建期 metadata 注入，"
           "本适配只装模块不建 dist-info）——如实报告，不臆造")
    elif ver == "1.0.1":
        ok("__version__ == '1.0.1'（与包版本一致）")
    else:
        fail("__version__ 既非 'unknown' 也非 '1.0.1'，实际 %r" % ver)

    total = 0
    for root, _dirs, files in os.walk(mod):
        total += sum(os.path.getsize(os.path.join(root, f)) for f in files)
    ok("证据：update_checker 模块总字节 %d；python %s" % (total, sys.version.split()[0]))

    print("\nchecks=%d fails=%d" % (checks, fails))
    print("RESULT: %s" % ("PASS" if fails == 0 else "FAIL"))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
