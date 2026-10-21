#!/usr/bin/env python3
"""消费测试 — vit 2.3.4 真实产物校验（全部离线，不触网）。

用法: python3 check_vit.py <package_folder>

检查交付物本身：命令齐备可执行、模块可导入且版本正确、入口参数解析可用（`--help`）、
核心组件（列表分批器/颜色映射）可真实调用、许可证随包、证据。任何一项不成立即 fail。
"""
import hashlib
import os
import subprocess
import sys

checks = fails = skips = 0


def ok(msg):
    global checks
    checks += 1
    print("[ok]   %s" % msg)


def sk(msg):
    global checks, skips
    checks += 1
    skips += 1
    print("[skip] %s" % msg)


def fail(msg):
    global checks, fails
    checks += 1
    fails += 1
    print("[FAIL] %s" % msg)


def run(cmd, env, stdin=None, timeout=300):
    return subprocess.run(cmd, capture_output=True, text=True, input=stdin,
                          timeout=timeout, env=env)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    pkg = sys.argv[1]
    pyroot = os.path.join(pkg, "python")
    env = dict(os.environ)
    env["PYTHONPATH"] = pyroot + (":" + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONWARNINGS"] = "ignore"
    env["TMPDIR"] = os.environ.get("TMPDIR", "/data/storage/el2/base/cache")
    env.setdefault("TERM", "dumb")
    exe = os.path.join(pkg, "bin", "vit")

    # ① 命令产物齐备且可执行
    if os.path.isfile(exe) and os.access(exe, os.X_OK):
        ok("命令产物齐备：bin/vit（%d 字节）" % os.path.getsize(exe))
    else:
        fail("缺少可执行命令：%s" % exe)

    # ② 模块可导入且版本正确
    try:
        r = run([sys.executable, "-c",
                 "import vit, vit.version; print(vit.version.VIT)"], env)
        out = ((r.stdout or "") + (r.stderr or "")).strip()
        if r.returncode == 0 and out.strip() == "2.3.4":
            ok("模块可导入且版本正确：vit.version.VIT = %s" % out.strip())
        else:
            fail("模块导入或版本不符（rc=%d）：%s" % (r.returncode, out[:200]))
    except Exception as exc:
        fail("模块导入检查异常：%s" % str(exc)[:160])

    # ③ 入口参数解析可用（--help 应正常退出并给出用法）
    try:
        r = run([sys.executable, "-c",
                 "import sys; sys.argv=['vit','--help']; from vit import parse_options; parse_options()"], env)
        out = ((r.stdout or "") + (r.stderr or "")).strip()
        if r.returncode == 0 and out and ("usage" in out.lower() or "vit" in out.lower()):
            ok("入口参数解析可用：`vit --help` 正常输出用法 ✓（首行：%s）" % out.splitlines()[0][:60])
        else:
            fail("`vit --help` 未给出用法（rc=%d）：%s" % (r.returncode, out[:200]))
    except Exception as exc:
        fail("入口参数解析检查异常：%s" % str(exc)[:160])

    # ④ 核心组件真实调用：列表分批器 + 颜色映射
    try:
        code = (
            "from vit.list_batcher import ListBatcher\n"
            "from vit.color_mappings import task_256_to_urwid_256\n"
            "b, to = ListBatcher(list('abc'), []), None\n"
            "assert b.add() is True\n"
            "m = task_256_to_urwid_256()\n"
            "assert m['gray'] == 'light gray'\n"
            "print('core OK')\n"
        )
        r = run([sys.executable, "-c", code], env)
        out = ((r.stdout or "") + (r.stderr or "")).strip()
        if r.returncode == 0 and "core OK" in out:
            ok("核心组件真实调用：ListBatcher 分批 + 颜色映射 ✓")
        else:
            fail("核心组件调用失败（rc=%d）：%s" % (r.returncode, out[:240]))
    except Exception as exc:
        fail("核心组件检查异常：%s" % str(exc)[:160])

    # ⑤ 许可证随包
    lic_dir = os.path.join(pkg, "licenses")
    lic = [f for f in os.listdir(lic_dir) if f.upper().startswith("LICEN")] if os.path.isdir(lic_dir) else []
    if lic:
        ok("许可证随包：licenses/%s" % lic[0])
    else:
        fail("缺少 licenses/ 下的许可证文件")

    # ⑥ 证据
    try:
        h = hashlib.sha256(open(exe, "rb").read()).hexdigest()
        ok("证据：bin/vit sha256=%s…；python %s" % (h[:16], sys.version.split()[0]))
    except Exception as exc:
        fail("证据收集失败：%s" % str(exc)[:120])

    print("\nchecks=%d fails=%d skips=%d" % (checks, fails, skips))
    print("RESULT: %s" % ("PASS" if fails == 0 else "FAIL"))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
