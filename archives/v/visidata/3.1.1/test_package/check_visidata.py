#!/usr/bin/env python3
"""消费测试 — visidata 3.1.1 真实产物校验（全部离线，不触网）。

用法: python3 check_visidata.py <package_folder>

检查交付物本身：命令齐备可执行（visidata + vd）、模块可导入且版本正确、命令真跑给出输出、
**真实批处理**（离线 CSV → 终端批处理导出）、许可证随包、证据。任何一项不成立即 fail。
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
    visidata = os.path.join(pkg, "bin", "visidata")
    vd = os.path.join(pkg, "bin", "vd")

    # ① 两个命令产物齐备且可执行
    missing = [p for p in (visidata, vd) if not (os.path.isfile(p) and os.access(p, os.X_OK))]
    if not missing:
        ok("命令产物齐备：bin/visidata + bin/vd")
    else:
        fail("缺少可执行命令：%s" % ", ".join(missing))

    # ② 模块可导入且版本正确
    try:
        r = run([sys.executable, "-c", "import visidata; print(visidata.__version__)"], env)
        out = ((r.stdout or "") + (r.stderr or "")).strip()
        if r.returncode == 0 and out.startswith("3.1.1"):
            ok("模块可导入且版本正确：visidata.__version__ = %s" % out.splitlines()[0][:20])
        else:
            fail("模块导入或版本不符（rc=%d）：%s" % (r.returncode, out[:200]))
    except Exception as exc:
        fail("模块导入检查异常：%s" % str(exc)[:160])

    # ③ 命令真跑：--version / --help / -h
    blob, rc, used = "", None, ""
    for flag in ("--version", "--help", "-h"):
        try:
            rr = run([visidata, flag], env)
        except Exception as exc:
            blob, rc, used = str(exc), -1, flag
            continue
        blob = ((rr.stdout or "") + (rr.stderr or "")).strip()
        rc, used = rr.returncode, flag
        if rc == 0 and blob:
            break
    if rc == 0 and blob:
        ok("真实运行：`visidata %s` rc=0 且有输出 ✓（首行：%s）" % (used, blob.splitlines()[0][:60]))
    else:
        fail("`visidata --version/--help/-h` 未成功（rc=%s）：%s" % (rc, blob[:200]))

    # ④ 真实批处理：离线 CSV 经 vd 批处理导出（不依赖网络与交互）
    try:
        csvp = os.path.join(env["TMPDIR"], "visidata_check_input.csv")
        outcsv = os.path.join(env["TMPDIR"], "visidata_check_output.csv")
        with open(csvp, "w", encoding="utf-8") as fh:
            fh.write("name,score\nfoo,1\nbar,2\n")
        r = run([vd, "-b", "-o", outcsv, csvp], env)
        produced = os.path.isfile(outcsv)
        content = ""
        if produced:
            content = open(outcsv, encoding="utf-8", errors="ignore").read().strip()
        if produced and "foo" in content and "bar" in content:
            ok("真实批处理：离线 CSV 经 `vd -b -o` 导出成功 ✓（输出含 foo/bar）")
        else:
            fail("批处理导出失败（rc=%d，produced=%s）：%s"
                 % (r.returncode, produced, ((r.stdout or "") + (r.stderr or ""))[:220]))
        for p in (csvp, outcsv):
            try:
                os.remove(p)
            except OSError:
                pass
    except Exception as exc:
        fail("批处理检查异常：%s" % str(exc)[:180])

    # ⑤ 许可证随包
    lic_dir = os.path.join(pkg, "licenses")
    lic = [f for f in os.listdir(lic_dir) if f.upper().startswith("LICEN")] if os.path.isdir(lic_dir) else []
    if lic:
        ok("许可证随包：licenses/%s" % lic[0])
    else:
        fail("缺少 licenses/ 下的许可证文件")

    # ⑥ 证据
    try:
        h = hashlib.sha256(open(visidata, "rb").read()).hexdigest()
        ok("证据：bin/visidata sha256=%s…；python %s" % (h[:16], sys.version.split()[0]))
    except Exception as exc:
        fail("证据收集失败：%s" % str(exc)[:120])

    print("\nchecks=%d fails=%d skips=%d" % (checks, fails, skips))
    print("RESULT: %s" % ("PASS" if fails == 0 else "FAIL"))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
