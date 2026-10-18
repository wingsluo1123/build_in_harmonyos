# uanytun

uAnytun 是 SATP（Secure Anycast Tunneling Protocol）的精简单线程实现：
把任意 ETHER TYPE 的报文封装进加密隧道（协议开销低于 IPSec Tunnel 模式），
主要面向小型平台做隧道客户端。`0.3.7` 配方把上游源码编译成命令行工具
`uanytun`（安装到 `sbin/`）。

## 适配要点

- **构建系统**：上游自带手写 `src/configure` + `src/Makefile`（非 autotools），
  只支持 `--target=Linux|OpenBSD|FreeBSD|...`，不认 `--host/--build` 交叉三元组；
  交叉编译由 conan profile 的编译器路径 + `make CC=<绝对路径>` 命令行覆盖实现。
- **加密后端**：使用上游默认的 libgcrypt（`--use-gcrypt`），依赖
  `libgcrypt/1.11.0`（传递依赖 `libgpg-error/1.55`）。上游同样支持
  nettle / OpenSSL crypto，本配方未启用。
- **传递依赖头路径**：`gcrypt.h` 会 `#include <gpg-error.h>`，
  因此必须把 libgpg-error 的 include 目录一并加入 CFLAGS。
- **无源码补丁**：`--target=Linux` 走 Linux TUN 分支，交叉编译一次通过。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.3.7 | built | 上游官方源码，无补丁 |

依赖：`libgcrypt/1.11.0`。许可证：GPL-3.0-or-later（OpenSSL 链接例外见上游 LICENSE.OpenSSL）。
