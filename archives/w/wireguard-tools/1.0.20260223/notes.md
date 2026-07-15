# wireguard-tools 1.0.20260223 适配笔记

## 编译环境
- 构建系统: makefile (纯 Makefile，无 configure 脚本)
- 编译日期: 2026-07-15
- 编译器: clang/clang++ (clang 15.0.4)
- 状态: built

## 编译步骤

1. 下载源码: `wireguard-tools-1.0.20260223.tar.xz` (官方 zx2c4.com)
2. 解压后进入 `src/` 目录（Makefile 在 src/ 下）
3. 创建 `ohos_compat.h` 兼容头文件（见下方问题 1）
4. 创建 `uapi/harmonyos -> uapi/linux` 符号链接（见下方问题 2）
5. 编译: `make V=1 -j1 PLATFORM=linux WITH_WGQUICK=yes WITH_BASHCOMPLETION=no WITH_SYSTEMDUNITS=no`
6. 安装: 手动复制 wg 二进制、wg-quick 脚本、man 页到包目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | sockaddr_storage 重复定义 | OHOS sys/socket.h 和 linux/socket.h 都定义了该结构体，linux/socket.h 缺少冲突保护 | 生成 ohos_compat.h，定义 _UAPI_LINUX_SOCKET_H 跳过 linux/socket.h，同时提供 __kernel_sa_family_t typedef |
| 2 | WGALLOWEDIP_A_FLAGS 未定义 | Makefile 检测 PLATFORM=harmonyos，但 uapi/harmonyos 目录不存在，无法找到 wireguard.h | 创建 uapi/harmonyos -> uapi/linux 符号链接，使 Makefile 的 -isystem uapi/$(PLATFORM) 生效 |
| 3 | PLATFORM 检测不匹配 | uname -s 返回 "harmonyos" 而非 "linux" | 传 PLATFORM=linux 给 make 命令 |
| 4 | wg-quick 不安装 | WITH_WGQUICK 默认空，检测 BINDIR/bash 失败 | 显式设置 WITH_WGQUICK=yes |

## 源码修改

无补丁。所有适配通过 conanfile.py 的 build() 方法动态生成文件和设置环境变量完成：
- `ohos_compat.h`: 在 build() 中用 conan.tools.files.save() 生成
- `uapi/harmonyos` 符号链接: 在 build() 中用 os.symlink() 创建

## 依赖版本

无外部依赖。仅依赖标准 C 库 (libc.so)。

## 验证结果

```bash
# 编译成功
$ make -C src V=1 -j1 PLATFORM=linux ...
clang ... -o wg

# 二进制测试
$ wg --help
Usage: wg <cmd> [<args>]
Available subcommands: show, showconf, set, setconf, ...

# 密钥生成测试（验证 curve25519 加密核心）
$ wg genkey
SD8HGaOmNj3n+e+1x8J53QlCs9ipg7bg+B0/ftmpQ2g=

$ echo "SD8HGaOmNj3n+e+1x8J53QlCs9ipg7bg+B0/ftmpQ2g=" | wg pubkey
i5L0B7cd0aFvDTFqtjnzCJX2a8PS0gF0CyuXgfZMsQQ=

$ wg genpsk
QKl+apL+hZZRreaJQXUvE7UdF3jw5ilOt2u1Jc2i3yw=

# 二进制信息
$ file wg
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped

$ readelf -d wg
NEEDED: libc.so
FLAGS: BIND_NOW
FLAGS_1: NOW PIE
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/wg | WireGuard 配置工具 (ELF aarch64) |
| bin/wg-quick | 快速启动脚本 (bash) |
| share/man/man8/wg.8 | wg 手册页 |
| share/man/man8/wg-quick.8 | wg-quick 手册页 |

## 注意事项

- wireguard-tools 仅提供用户空间工具，实际 VPN 功能需要 WireGuard 内核模块支持
- 鸿蒙平台可能缺少 WireGuard 内核模块，工具可编译但实际功能依赖内核支持
- wg-quick 为 bash 脚本，需 bash 环境才能运行
- ELF 签名: package() 方法中使用 binary-sign-tool 对 wg 二进制进行签名
---

**编译结束**: 2026-07-15 20:20
**最终状态**: built
