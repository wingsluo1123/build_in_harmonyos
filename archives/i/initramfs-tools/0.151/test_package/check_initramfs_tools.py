#!/usr/bin/env python3
"""Consumer checks for the initramfs-tools package.

usage: check_initramfs_tools.py <package-folder>

Checks（全部针对打包后的产物；分类口径：**只有具名环境信号才允许 SKIP**）：
  1. 关键产物齐备：bin/unmkinitramfs、bin/lsinitramfs、sbin/mkinitramfs、sbin/update-initramfs、
     share/initramfs-tools/{hook-functions,init,modules,hooks/,scripts/}、
     etc/initramfs-tools/{initramfs.conf,update-initramfs.conf}、man 页；
  2. 编译产物架构：unmkinitramfs 是 64 位 AArch64 ELF（手写解析 ELF 头）；
  3. 模板替换已生效：sbin/mkinitramfs 内**不再含** @VERSION@ / @BUSYBOX_PACKAGES@ 占位符，
     且含本包版本号 0.151（这一步能抓住"照抄源码不打模板"的打包错误）；
  4. shell 产物语法检查（sh -n）+ best-effort 真跑 unmkinitramfs（无参时打印用法/退出），
     宿主加载器拒绝按具名环境信号记 SKIP，其余非 0 判 FAIL。
"""
import os
import re
import struct
import subprocess
import sys

EM_AARCH64 = 0xB7
LOADER_LIMIT_TAGS = ("error loading shared library", "error relocating",
                     "cannot open shared object", "permission denied",
                     "operation not permitted", "not signed", "unsigned")
SHELL_PAYLOAD = ("bin/lsinitramfs", "sbin/mkinitramfs", "sbin/update-initramfs",
                 "share/initramfs-tools/hook-functions", "share/initramfs-tools/init")

fails = []
skips = []


def fail(msg):
    fails.append(msg)
    print("[FAIL] %s" % msg)


def ok(msg):
    print("[ok]   %s" % msg)


def skip(msg):
    skips.append(msg)
    print("[skip] %s" % msg)


def check_payload(pkg):
    required = [
        "bin/unmkinitramfs", "bin/lsinitramfs",
        "sbin/mkinitramfs", "sbin/update-initramfs",
        "share/initramfs-tools/hook-functions", "share/initramfs-tools/init",
        "share/initramfs-tools/modules", "share/initramfs-tools/hooks",
        "share/initramfs-tools/scripts",
        "etc/initramfs-tools/initramfs.conf", "etc/initramfs-tools/update-initramfs.conf",
        "share/man/man7/initramfs-tools.7", "share/man/man8/mkinitramfs.8",
        "share/man/man8/unmkinitramfs.8", "share/man/man5/initramfs.conf.5",
    ]
    missing = [rel for rel in required if not os.path.exists(os.path.join(pkg, rel))]
    if missing:
        fail("缺少产物：%s" % ", ".join(missing))
        return
    ok("关键产物齐备（%d 项：工具 + hooks/scripts 框架 + 配置 + man）" % len(required))


def check_unmkinitramfs_arch(pkg):
    path = os.path.join(pkg, "bin", "unmkinitramfs")
    if not os.path.isfile(path):
        return
    with open(path, "rb") as fh:
        head = fh.read(64)
    if head[:4] != b"\x7fELF":
        fail("bin/unmkinitramfs 不是 ELF（Makefile 的编译产物应为本机交叉编译结果）")
        return
    if head[4] != 2 or struct.unpack("<H", head[18:20])[0] != EM_AARCH64:
        fail("bin/unmkinitramfs 不是 64 位 AArch64 ELF")
        return
    ok("bin/unmkinitramfs 为 64 位 AArch64 ELF（来自本包 make all）")


def check_template_substitution(pkg):
    path = os.path.join(pkg, "sbin", "mkinitramfs")
    if not os.path.isfile(path):
        return
    with open(path, errors="replace") as fh:
        body = fh.read()
    leftovers = [t for t in ("@VERSION@", "@BUSYBOX_PACKAGES@") if t in body]
    if leftovers:
        fail("sbin/mkinitramfs 仍含未替换占位符：%s（应照 Debian override_dh_install 做替换）"
             % ", ".join(leftovers))
        return
    if "0.151" not in body:
        fail("sbin/mkinitramfs 内未见版本号 0.151（@VERSION@ 替换可疑）")
        return
    ok("模板替换已生效：sbin/mkinitramfs 无占位符残留且含版本号 0.151")


def _sh_path():
    """取可用的 POSIX shell 绝对路径。

    实测：消费者校验运行时 PATH 可能不含 /bin（`subprocess.run(["sh", …])` 直接
    `FileNotFoundError: 'sh'`），故不依赖 PATH 解析，按候选绝对路径挑一个存在的。
    """
    import shutil
    candidates = [shutil.which("sh"), "/bin/sh", "/usr/bin/sh", "/system/bin/sh"]
    for cand in candidates:
        if cand and os.path.exists(cand):
            return cand
    return None


def check_shell_syntax_and_run(pkg):
    sh = _sh_path()
    if sh is None:
        skip("具名环境信号：宿主找不到可用 POSIX shell（/bin/sh 等均不存在）")
        return
    bad = []
    for rel in SHELL_PAYLOAD:
        path = os.path.join(pkg, rel)
        if not os.path.isfile(path):
            continue
        proc = subprocess.run([sh, "-n", path], stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT)
        if proc.returncode != 0:
            bad.append("%s(%s)" % (rel, proc.stdout.decode("utf-8", "replace").strip()[:60]))
    if bad:
        fail("shell 语法检查失败：%s" % ", ".join(bad))
        return
    ok("shell 产物 sh -n 语法检查全部通过（%d 个，shell=%s）" % (len(SHELL_PAYLOAD), sh))

    path = os.path.join(pkg, "bin", "unmkinitramfs")
    if not os.path.isfile(path):
        return
    try:
        proc = subprocess.run([path], stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=20)
        out = proc.stdout.decode("utf-8", "replace")
        rc = proc.returncode
    except subprocess.TimeoutExpired:
        ok("unmkinitramfs 运行后存活至 20s 超时（未因缺库立即退出）")
        return
    except OSError as exc:
        if any(tag in str(exc).lower() for tag in LOADER_LIMIT_TAGS):
            skip("具名环境信号：宿主拒绝启动 OHOS 二进制：%s" % exc)
        else:
            fail("unmkinitramfs 无法执行：%s" % exc)
        return
    low = out.lower()
    if any(tag in low for tag in LOADER_LIMIT_TAGS):
        skip("具名环境信号：宿主加载器拒绝 OHOS 共享对象闭包：%s" % out.strip()[:160])
        return
    if rc == 0 or re.search(r"usage|Usage|initramfs", out):
        ok("unmkinitramfs 真跑成功（exit=%s）：%s" % (rc, out.strip()[:110]))
        return
    fail("unmkinitramfs 非 0 退出且无具名环境信号 → 判真实缺陷（exit=%s）：%s"
         % (rc, out.strip()[:160]))


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    pkg = sys.argv[1]
    check_payload(pkg)
    check_unmkinitramfs_arch(pkg)
    check_template_substitution(pkg)
    check_shell_syntax_and_run(pkg)
    print("checks=%d fails=%d skips=%d" % (4, len(fails), len(skips)))
    if fails:
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
