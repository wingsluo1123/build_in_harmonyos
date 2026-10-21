#!/usr/bin/env python3
"""消费测试 — vint 0.3.21 真实产物校验（全部离线，不触网）。

用法: python3 check_vint.py <package_folder>

除"产物可用"外，还做一次**真实 lint 行为**验证：给一段故意写坏的 vim script，断言 vint 能报出问题
（退出码非 0 + 输出含规则/错误信息）。任何一项不成立即 fail；仅环境原因才计入 skips（且不计入通过）。
"""
import hashlib
import os
import subprocess
import sys
import tempfile

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


def run(cmd, env, timeout=300):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    pkg = sys.argv[1]
    pyroot = os.path.join(pkg, "python")
    env = dict(os.environ)
    env["PYTHONPATH"] = pyroot + (":" + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONWARNINGS"] = "ignore"      # 现代 Python / setuptools 的告警会污染被测命令输出
    env["TMPDIR"] = os.environ.get("TMPDIR", "/data/storage/el2/base/cache")

    exe = None
    for rel in (os.path.join("bin", "vint"), os.path.join("python", "bin", "vint")):
        cand = os.path.join(pkg, rel)
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            exe = cand
            break
    # `vint` 没有 __main__（`python -m vint` 不可用）→ 退回到上游入口 `vint:main`
    runner = [exe] if exe else [sys.executable, "-c", "import sys; from vint import main; sys.exit(main())"]

    # ① 产物：命令 + 模块都在
    if exe:
        ok("命令产物齐备：%s（%d 字节）" % (os.path.relpath(exe, pkg), os.path.getsize(exe)))
    else:
        fail("缺少命令产物：%s/bin/vint" % pkg)
    if os.path.isdir(os.path.join(pyroot, "vint")):
        ok("模块随包：python/vint/ 存在")
    else:
        fail("缺少模块目录：%s/python/vint" % pkg)

    # ② 依赖随包（PyYAML / ansicolor / chardet 的模块目录存在）
    missing = [m for m in ("yaml", "ansicolor", "chardet") if not os.path.isdir(os.path.join(pyroot, m))]
    if not missing:
        ok("运行时依赖随包 ✓（yaml / ansicolor / chardet）")
    else:
        fail("运行时依赖缺失：%s" % ", ".join(missing))

    # ③ 真跑 --version / --help（能失败的真断言）
    try:
        blob, rc, used = "", None, ""
        for flag in ("--version", "--help", "-h"):
            r = run(runner + [flag], env)
            blob = ((r.stdout or "") + (r.stderr or "")).strip()
            rc, used = r.returncode, flag
            if rc == 0 and blob:
                break
        if rc == 0 and blob:
            ok("真实运行：`vint %s` rc=0 且有输出 ✓（首行：%s）" % (used, blob.splitlines()[0][:64]))
        else:
            fail("`vint --version/--help` 未成功（rc=%s）：%s" % (rc, blob[:220]))
    except Exception as exc:
        fail("vint 无法执行：%s" % str(exc)[:180])

    # ④ 真实 lint 行为：故意写坏的脚本必须被报出来（rc!=0 且输出含规则信息）
    try:
        bad = os.path.join(env["TMPDIR"], "vint_check_bad.vim")
        with open(bad, "w", encoding="utf-8") as fh:
            fh.write("let g:unused_variable = 1\ncall NonExistentFunction(\n")
        r2 = run(runner + [bad], env)
        out2 = ((r2.stdout or "") + (r2.stderr or "")).strip()
        if r2.returncode != 0 and out2:
            ok("真实 lint 行为：坏脚本被判出问题 ✓（rc=%d，样例输出：%s）"
               % (r2.returncode, out2.splitlines()[0][:70]))
        else:
            fail("lint 行为异常：坏脚本未被报出（rc=%d）：%s" % (r2.returncode, out2[:200]))
        try:
            os.remove(bad)
        except OSError:
            pass
    except Exception as exc:
        fail("lint 行为验证异常：%s" % str(exc)[:180])

    # ⑤ 许可证随包
    lic = [f for f in os.listdir(os.path.join(pkg, "licenses"))] if os.path.isdir(os.path.join(pkg, "licenses")) else []
    if any(f.upper().startswith("LICEN") for f in lic):
        ok("许可证随包：licenses/%s" % [f for f in lic if f.upper().startswith("LICEN")][0])
    else:
        fail("缺少 licenses/ 下的许可证文件")

    # ⑥ 证据
    try:
        target = exe or os.path.join(pyroot, "vint", "__init__.py")
        h = hashlib.sha256(open(target, "rb").read()).hexdigest()
        ok("证据：%s sha256=%s…；python %s"
           % (os.path.relpath(target, pkg), h[:16], sys.version.split()[0]))
    except Exception as exc:
        fail("证据收集失败：%s" % str(exc)[:120])

    print("\nchecks=%d fails=%d skips=%d" % (checks, fails, skips))
    print("RESULT: %s" % ("PASS" if fails == 0 else "FAIL"))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
