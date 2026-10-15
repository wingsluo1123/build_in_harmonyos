#!/usr/bin/env python3
"""消费测试 — pooch 1.9.0 真实产物校验（全部离线，不触网）。

用法: python3 check_pooch.py <package_folder>
"""
import hashlib
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
        if os.path.basename(root) == "pooch":
            mod = root
            break
    if not mod or not os.path.isdir(mod):
        fail("产物缺失：site-packages 下找不到 pooch/ 模块目录")
        print("\nchecks=%d fails=%d skips=%d\nRESULT: FAIL" % (checks, fails, skips))
        return 1
    ok("产物齐备：pooch 模块位于 %s" % os.path.relpath(mod, pkg))

    need = ("__init__.py", "core.py", "downloaders.py", "hashes.py",
            "processors.py", "utils.py", "_version.py")
    miss = [n for n in need if not os.path.exists(os.path.join(mod, n))]
    if miss:
        fail("关键文件缺失：%s" % miss)
    else:
        ok("关键文件齐备：%s" % " / ".join(need))

    site_root = os.path.dirname(mod)
    sys.path.insert(0, site_root)
    try:
        import pooch
        ok("import pooch 成功（依赖 platformdirs/packaging/requests 由 conan requires 提供）")
    except Exception as exc:
        fail("import pooch 失败：%s" % str(exc)[:160])
        print("\nchecks=%d fails=%d skips=%d\nRESULT: FAIL" % (checks, fails, skips))
        return 1

    ver = getattr(pooch, "__version__", None)
    # 上游 pooch/__init__.py 里是 `__version__ = f"v{_version.version}"`
    # （_version.py 由 setuptools-scm 生成）→ 实测为 'v1.9.0'；这里同时接受去掉前缀的写法
    if ver is not None and ver.lstrip("v") == "1.9.0":
        ok("__version__ == %r（上游 f\"v{_version.version}\"，与包版本 1.9.0 一致）" % ver)
    else:
        fail("__version__ 期望 v1.9.0（或 1.9.0），实际 %r" % ver)

    # 真实离线 API 1：以确定内容计算哈希（真跑 hashes 模块）
    tmp = os.path.join(os.environ.get("TMPDIR", "/data/storage/el2/base/cache"),
                       "pooch-consumer-check.txt")
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    payload = b"atomcode-consumer-test\n"
    with open(tmp, "wb") as fh:
        fh.write(payload)
    want = hashlib.sha256(payload).hexdigest()
    try:
        got = pooch.file_hash(tmp, alg="sha256")
        if got == want:
            ok("真实离线 API：pooch.file_hash() 计算 sha256 正确（%s…）" % got[:16])
        else:
            fail("pooch.file_hash() 结果不符：%s != %s" % (got, want))
    except Exception as exc:
        fail("pooch.file_hash() 调用失败：%s" % str(exc)[:160])

    # 真实离线 API 2：构造 Pooch 对象（不下载，纯本地）
    try:
        cache = os.path.join(os.environ.get("TMPDIR", "/data/storage/el2/base/cache"),
                             "pooch-consumer-cache")
        os.makedirs(cache, exist_ok=True)
        p = pooch.create(path=cache, base_url="https://example.invalid/",
                         registry={"data.txt": want}, env=None)
        if hasattr(p, "registry") and p.registry.get("data.txt") == want:
            ok("真实离线 API：pooch.create() 构造成功并保留 registry（无网络访问）")
        else:
            fail("pooch.create() 返回对象的 registry 不符预期")
    except Exception as exc:
        fail("pooch.create() 调用失败：%s" % str(exc)[:160])

    total = 0
    for root, _dirs, files in os.walk(mod):
        total += sum(os.path.getsize(os.path.join(root, f)) for f in files)
    ok("证据：pooch 模块总字节 %d；python %s" % (total, sys.version.split()[0]))

    print("\nchecks=%d fails=%d skips=%d" % (checks, fails, skips))
    print("RESULT: %s" % ("PASS" if fails == 0 else "FAIL"))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
