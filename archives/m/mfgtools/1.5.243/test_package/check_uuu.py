#!/usr/bin/env python3
"""消费测试 — mfgtools(uuu) 1.5.243 真实产物校验（全部离线，不触网）。

用法: python3 check_uuu.py <package_folder>
"""
import glob
import hashlib
import os
import shutil
import subprocess
import sys

checks = fails = skips = 0

# libusb 打桩源码 —— 与配方 conanfile.py 里的 `_USB_STUB_C` **保持一致**（两处必须同步改）。
# 背景：uuu 在解析参数**之前**就 libusb_init（libuuu/usbhotplug.cpp:77），无 USB 子系统的环境
# 必然抛 std::runtime_error 直接 abort（rc=134）→ 连 `-h`/`-V` 都跑不到。打桩只让 USB
# 初始化/热插拔注册/设备枚举“成功且无设备”，使**真实二进制**的 CLI 路径能真正执行；不伪造设备。
USB_STUB_C = r"""#include <stddef.h>
typedef void *libusb_context;
typedef void *libusb_hotplug_callback_handle;
int libusb_init(libusb_context **ctx) { if (ctx) *ctx = (libusb_context)0x1; return 0; }
int libusb_init_context(libusb_context **ctx, const void *o, int n) { (void)o; (void)n; return libusb_init(ctx); }
void libusb_exit(libusb_context *ctx) { (void)ctx; }
int libusb_set_option(libusb_context *ctx, int option, ...) { (void)ctx; (void)option; return 0; }
int libusb_hotplug_register_callback(libusb_context *ctx, int e, int f, int v, int p, int c,
                                     void *cb, void *ud, libusb_hotplug_callback_handle *h)
{ (void)ctx; (void)e; (void)f; (void)v; (void)p; (void)c; (void)cb; (void)ud; if (h) *h = (libusb_hotplug_callback_handle)0x1; return 0; }
void libusb_hotplug_deregister_callback(libusb_context *ctx, libusb_hotplug_callback_handle h) { (void)ctx; (void)h; }
int libusb_get_device_list(libusb_context *ctx, void ***list) { (void)ctx; if (list) *list = NULL; return 0; }
void libusb_free_device_list(void **list, int u) { (void)list; (void)u; }
const char *libusb_error_name(int e) { (void)e; return "stub"; }
"""


def build_usb_stub(work):
    cc = shutil.which("clang") or shutil.which("cc") or shutil.which("gcc") or \
        "/data/service/hnp/bin/clang"
    os.makedirs(work, exist_ok=True)
    src = os.path.join(work, "libusbstub.c")
    so = os.path.join(work, "libusbstub.so")
    with open(src, "w", encoding="utf-8") as fh:
        fh.write(USB_STUB_C)
    r = subprocess.run([cc, "-shared", "-fPIC", "-o", so, src],
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0 or not os.path.isfile(so):
        raise RuntimeError("编译 libusb 打桩失败（rc=%d）：%s" % (r.returncode, (r.stderr or "")[:200]))
    return so


def ok(msg):
    global checks
    checks += 1
    print("[ok]   %s" % msg)


def sk(msg):
    """环境原因导致本项无法判定（如无 USB 子系统）：单独计入 skips，**不计入通过**。"""
    global checks, skips
    checks += 1
    skips += 1
    print("[skip] %s" % msg)


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
    exe = os.path.join(pkg, "bin", "uuu")

    # ① 产物
    if os.path.isfile(exe) and os.access(exe, os.X_OK):
        ok("产物齐备：bin/uuu 存在且可执行（%d 字节）" % os.path.getsize(exe))
    else:
        fail("缺少可执行产物：%s" % exe)
        print("\nchecks=%d fails=%d\nRESULT: FAIL" % (checks, fails))
        return 1

    # ② ELF 头自检
    try:
        with open(exe, "rb") as fh:
            h = fh.read(20)
        magic, cls, machine = h[:4], h[4], int.from_bytes(h[18:20], "little")
        if magic == b"\x7fELF" and cls == 2 and machine == 0xB7:
            ok("ELF 头自检：真 ELF64、machine=0xB7(AArch64) ✓")
        else:
            fail("ELF 头不符合预期：magic=%r class=%d machine=0x%x" % (magic, cls, machine))
    except Exception as exc:
        fail("ELF 头读取失败：%s" % str(exc)[:160])

    # ③a 原生运行（不打桩）：无 USB 子系统时 uuu 在解析参数前 libusb_init 失败 → 单独记 skip
    try:
        r0 = subprocess.run([exe, "-h"], capture_output=True, text=True, timeout=300)
        out0 = r0.stdout + r0.stderr
        if r0.returncode == 0 and out0.strip():
            ok("原生运行：`uuu -h` rc=0 且有输出（首行：%s）" % out0.strip().splitlines()[0][:70])
        elif "libusb_init failure" in out0 or "libusb" in out0.lower():
            sk("原生运行 `uuu -h` 在本环境无法完成（rc=%d：无 USB 子系统，而 uuu 在解析参数前就 "
               "libusb_init → 抛异常 abort）——单独记 skip，**不计入通过**" % r0.returncode)
        else:
            fail("原生 `uuu -h` 异常（rc=%d）：%s" % (r0.returncode, out0.strip()[:200]))
    except Exception as exc:
        fail("uuu 无法执行：%s" % str(exc)[:200])

    # ③b 打桩 libusb 后，真实二进制的 CLI 路径**必须真跑通**（能失败的真断言）
    env2 = dict(os.environ)
    try:
        stub = build_usb_stub(os.path.join(os.environ.get("TMPDIR") or ".", "uuu-usb-stub"))
    except Exception as exc:
        stub = None
        fail("构建 libusb 打桩失败，CLI 路径无法验证：%s" % str(exc)[:180])
    if stub:
        env2["LD_PRELOAD"] = stub
        try:
            r1 = subprocess.run([exe, "-h"], capture_output=True, text=True, timeout=300, env=env2)
            out1 = r1.stdout + r1.stderr
            if r1.returncode == 0 and "Universal Update Utility" in out1:
                ok("打桩 libusb 后**真跑通**：`uuu -h` rc=0 且打印上游用法 ✓（首行：%s）"
                   % out1.strip().splitlines()[0][:70])
            else:
                fail("打桩后 `uuu -h` 仍未跑通（rc=%d）：%s" % (r1.returncode, out1.strip()[:200]))
            # 版本横幅：从 `-h` 的输出里校验（形如 `… -- lib<版本>`）。
            # ⚠️ 不用 `uuu -V`：上游 uuu.cpp:187 写明 `-V` 是 libusb 详细日志开关，不是版本。
            _mark = " -- lib"
            _tail = out1.split(_mark, 1)[1] if _mark in out1 else ""
            if _tail[:1].isdigit():
                ok("`uuu -h` 横幅含 libuuu 版本 ✓（%s）" % _tail.splitlines()[0].strip()[:60])
            else:
                fail("`uuu -h` 横幅里没有版本串（rc=%d）：%s" % (r1.returncode, out1.strip()[:200]))
        except Exception as exc:
            fail("打桩后执行 uuu 异常：%s" % str(exc)[:200])

    # ④ 不带参数时的行为（应给出用法/错误提示，而非静默崩溃）
    try:
        r = subprocess.run([exe], capture_output=True, text=True, timeout=300,
                           env=(env2 if stub else None))
        blob = ((r.stdout or "") + (r.stderr or "")).strip()
        if blob:
            ok("无参调用有明确输出（rc=%d）——非静默退出" % r.returncode)
        else:
            fail("无参调用没有任何输出（rc=%d）" % r.returncode)
    except Exception as exc:
        fail("无参调用异常：%s" % str(exc)[:200])

    # ⑤ 许可证随包
    lic = os.path.join(pkg, "licenses", "LICENSE")
    if os.path.isfile(lic):
        ok("许可证随包：licenses/LICENSE 存在")
    else:
        fail("缺少 licenses/LICENSE")

    # ⑥ 证据
    try:
        h = hashlib.sha256(open(exe, "rb").read()).hexdigest()
        ok("证据：bin/uuu sha256=%s…；python %s" % (h[:16], sys.version.split()[0]))
    except Exception as exc:
        fail("证据收集失败：%s" % str(exc)[:120])

    print("\nchecks=%d fails=%d skips=%d" % (checks, fails, skips))
    print("RESULT: %s" % ("PASS" if fails == 0 else "FAIL"))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
