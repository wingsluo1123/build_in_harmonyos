#!/usr/bin/env python3
"""websocket.so 打包产物校验（L1 消费者视角）。

模块 .so 由 kamailio 二进制运行时 dlopen（WS/WSS 握手需要运行中的 kamailio 与
SIP 场景），故按产物结构做实质校验：ELF 架构、OpenSSL 静态链入证据、
libunistring 静态链入证据、模块 API 导出符号、许可证文件与宿主路径泄漏检查。
"""
import os
import shutil
import subprocess
import sys

FAILURES = []


def check(cond, label, detail=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
    if not cond:
        FAILURES.append(label)


def main():
    module = os.environ["KAMAILIO_WEBSOCKET_MODULE"]
    pkg = os.environ["KAMAILIO_WEBSOCKET_PACKAGE_FOLDER"]

    with open(module, "rb") as fh:
        blob = fh.read()
    print(f"artifact: {module} ({len(blob)} bytes)")

    # 1) ELF 结构：64 位 / 可重定位共享对象 / AArch64
    check(blob[:4] == b"\x7fELF", "ELF 魔数")
    check(blob[4] == 2, "ELFCLASS64", f"ei_class={blob[4]}")
    e_type = int.from_bytes(blob[16:18], "little")
    check(e_type == 3, "ET_DYN（共享对象）", f"e_type={e_type}")
    e_machine = int.from_bytes(blob[18:20], "little")
    check(e_machine == 0xB7, "e_machine=AArch64", f"e_machine={e_machine}")

    # 2) OpenSSL 静态链入证据：libssl/libcrypto 符号已并入本模块（NEEDED 仅 libc.so）
    #    ws_handshake.c 直接调用 SHA1() 计算 WS 握手 key（openssl/sha.h）；
    #    EVP_sha1/EVP_sha256 与 OPENSSL_init_crypto/OPENSSL_cleanup 为 OpenSSL 3.x
    #    静态链入的 libcrypto 符号；mod_register 是 kamailio 模块入口符号。
    for marker in (b"SHA1", b"EVP_sha1", b"OPENSSL_init_crypto",
                   b"OPENSSL_cleanup", b"mod_register"):
        check(marker in blob, f"符号标记 {marker.decode()}")

    # 3) libunistring 静态链入证据（ws_frame.c #include <unistr.h> 的 u8_check）
    check(b"u8_check" in blob, "符号标记 u8_check")

    # 4) 许可证随包安装
    check(os.path.isfile(os.path.join(pkg, "licenses", "COPYING")), "licenses/COPYING 存在")

    # 5) 工具链侧复核（存在则执行，提供动态段附加证据）
    readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
    if readelf:
        out = subprocess.run([readelf, "-d", module], capture_output=True, text=True).stdout
        needed = [ln.split("[")[-1].rstrip("] \n") for ln in out.splitlines() if "NEEDED" in ln]
        check(all("libssl" not in n and "libcrypto" not in n
                  and "libunistring" not in n for n in needed),
              "依赖静态链入（NEEDED 无 libssl/libcrypto/libunistring）",
              ", ".join(needed) or "libc.so only")
        # 交叉编译产物不得内嵌构建机路径（RPATH/RUNPATH 泄漏 = 目标机加载失败）
        check(not any(k in out for k in ("RPATH", "RUNPATH")),
              "动态段无 RPATH/RUNPATH", "clean")
    else:
        print("[SKIP] 未找到 readelf/llvm-readelf，跳过动态段复核")

    if FAILURES:
        print(f"\nFAILED: {len(FAILURES)} 项 — {FAILURES}")
        return 1
    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
