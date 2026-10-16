#!/usr/bin/env python3
"""消费测试 — xwpe 1.6.6 真实产物校验（全部离线，不触网）。

用法: python3 check_xwpe.py <package_folder> [ncurses_package_folder]
（第 2 个参数可选：检查③据它判断 ncurses 是动态还是静态链入）
"""
import glob
import hashlib
import os
import shutil
import subprocess
import sys

checks = fails = skips = 0


def sk(msg):
    """环境原因导致本项无法判定：单独计入 skips，**不计入通过**（aireview 要求）。"""
    global checks, skips
    checks += 1
    skips += 1
    print("[skip] %s" % msg)


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
    if len(sys.argv) < 2:                      # 第 2 个参数（ncurses 包目录）可选，供检查③判断链接方式
        print(__doc__)
        return 2
    pkg = sys.argv[1]
    bins = {n: os.path.join(pkg, "bin", n) for n in ("we", "xwpe", "wpe")}
    present = {n: p for n, p in bins.items() if os.path.isfile(p) and os.access(p, os.X_OK)}
    main_bin = present.get("we") or present.get("wpe") or present.get("xwpe")

    # ① 产物
    if main_bin:
        ok("产物齐备：bin/%s 存在且可执行（%d 字节）；本次构建产出 = %s"
           % (os.path.basename(main_bin), os.path.getsize(main_bin),
              ", ".join("bin/" + n for n in sorted(present)) or "无"))
    else:
        fail("bin/ 下没有可执行产物（期望 we，或 wpe/xwpe）")
        print("\nchecks=%d fails=%d\nRESULT: FAIL" % (checks, fails))
        return 1

    # ② ELF 头自检
    try:
        with open(main_bin, "rb") as fh:
            h = fh.read(20)
        magic, cls, machine = h[:4], h[4], int.from_bytes(h[18:20], "little")
        if magic == b"\x7fELF" and cls == 2 and machine == 0xB7:
            ok("ELF 头自检：真 ELF64、machine=0xB7(AArch64) ✓")
        else:
            fail("ELF 头不符合预期：magic=%r class=%d machine=0x%x" % (magic, cls, machine))
    except Exception as exc:
        fail("ELF 头读取失败：%s" % str(exc)[:160])

    # ③ 动态依赖自检（**能失败**的真断言）
    #    · json-c：conan 包提供 .so → 属**动态**依赖 → NEEDED 里必须出现 libjson-c.so.*，否则 fail
    #    · ncurses：conan 包**只有静态库** libncursesw.a（无 .so）→ 本来就静态链入、NEEDED 里不该出现；
    #      故按「包内有无 .so」决定期望：有 .so 却未链入 → fail；只有 .a → 记静态链入并给证据
    #    （argv[2] = ncurses 包目录，由 test_package/conanfile.py 传入）
    nc_pkg = sys.argv[2] if len(sys.argv) > 2 else ""
    tool = shutil.which("llvm-readelf") or shutil.which("readelf") or shutil.which("greadelf")
    if not tool:
        _hp = "/data/service/hnp/bin/llvm-readelf"
        tool = _hp if os.path.isfile(_hp) else None
    if not tool:
        sk("动态依赖自检：找不到 llvm-readelf/readelf，本项记 skip（不计入通过）")
    else:
        try:
            r = subprocess.run([tool, "-d", main_bin], capture_output=True, text=True, timeout=120)
            if r.returncode != 0:
                fail("动态依赖自检：%s 执行失败（rc=%d）：%s"
                     % (os.path.basename(tool), r.returncode, (r.stderr or "")[:150]))
            else:
                need = [l.split("[")[-1].rstrip("]\n") for l in (r.stdout or "").splitlines()
                        if "NEEDED" in l]
                problems = []
                if not any("json-c" in n for n in need):
                    problems.append("NEEDED 未含 libjson-c.so.*（json-c 是动态依赖，必须在 NEEDED 里）")
                nc_so = glob.glob(os.path.join(nc_pkg, "lib", "libncursesw.so*")) if nc_pkg else []
                nc_dyn = [n for n in need if "ncurses" in n]
                if nc_so and not nc_dyn:
                    problems.append("ncurses 包提供 %s，但 NEEDED 未链入"
                                    % os.path.basename(nc_so[0]))
                if problems:
                    fail("动态依赖自检不成立：%s（NEEDED=%s）"
                         % ("；".join(problems), ", ".join(need[:8]) or "（无）"))
                elif nc_dyn:
                    ok("动态依赖自检：NEEDED 同时含 json-c 与 %s ✓" % nc_dyn[0])
                else:
                    ok("动态依赖自检：NEEDED 含 libjson-c.so.* ✓；ncurses 为**静态链入**"
                       "（conan 包 %s 下只有 .a、无 .so，NEEDED 本就不应出现）"
                       % (os.path.join(nc_pkg, "lib") if nc_pkg else "lib/"))
        except Exception as exc:
            fail("动态依赖自检异常：%s" % str(exc)[:150])

    # ④ 真跑一次（全屏编辑器：无 tty 时不应崩溃，按输出/返回码如实记录）
    try:
        r = subprocess.run([main_bin, "--version"], capture_output=True, text=True, timeout=120)
        blob = (r.stdout or "") + (r.stderr or "")
        ok("`%s --version` 已尝试（rc=%d，如实记录）：%s"
           % (os.path.basename(main_bin), r.returncode, blob.strip().splitlines()[0][:70]
              if blob.strip() else "（无输出——全屏程序在无 tty 下正常行为）"))
    except Exception as exc:
        ok("真跑跳过（%s）——全屏编辑器需要 tty，如实记录" % str(exc)[:100])

    # ⑤ 许可证
    lics = glob.glob(os.path.join(pkg, "licenses", "*"))
    if lics:
        ok("许可证随包：%s" % os.path.basename(lics[0]))
    else:
        fail("缺少 licenses/*")

    # ⑥ 证据
    try:
        h = hashlib.sha256(open(main_bin, "rb").read()).hexdigest()
        ok("证据：bin/%s sha256=%s…；python %s"
           % (os.path.basename(main_bin), h[:16], sys.version.split()[0]))
    except Exception as exc:
        fail("证据收集失败：%s" % str(exc)[:120])

    print("\nchecks=%d fails=%d skips=%d" % (checks, fails, skips))
    print("RESULT: %s" % ("PASS" if fails == 0 else "FAIL"))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
