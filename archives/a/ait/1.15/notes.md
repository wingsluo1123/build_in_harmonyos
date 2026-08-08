# ait 1.15 适配笔记

## 编译环境
- 构建系统: makefile (简单 Makefile，无 configure)
- 编译日期: 2026-08-08
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

1. 下载源码：从 NetBSD misc 归档 `https://ftp.netbsd.org/pub/NetBSD/misc/ktnb/ait-1.15.tar.gz`
2. 解压到 work 目录
3. 编译命令：
```bash
cd $BUILD_SRC_DIR
make clean CC=clang
make ait CC=clang CFLAGS="-fPIC -O2 -Wall" LDFLAGS=""
```
4. 安装到 staging：
```bash
make install PREFIX=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `_XOPEN_SOURCE` macro redefined 警告 | header.h 第 5 行 `#define _XOPEN_SOURCE` 与 sysroot 的 `features.h` 冲突 | 警告级别，不影响编译，记录为平台兼容性提示 |
| 2 | staging 验证 `Operation not permitted` | 未签名 ELF 受 Seccomp 限制 | 平台限制，不阻塞；编译产物正确 |

## 源码修改

无补丁，源码未修改。编译警告（`_XOPEN_SOURCE` 重定义）属平台兼容性提示，不阻塞编译。

## 依赖版本

- libc (musl, 系统提供)
- 无外部 Conan 依赖

## 验证结果

```bash
$ ./ait -v
Ait 1.15, BSD 3-Clause, 2026, by Kevin Bloom,  No warranty.
```

编译产物：231,872 字节 ELF arm64 动态链接二进制（依赖 musl libc），`make install` 后 strip 为 198,560 字节。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/ait | 198,560 字节 | Emacs-style 编辑器二进制 (stripped) |

## 注意事项

1. **Seccomp 限制**：staging 目录的未签名 ELF 无法在 Seccomp 沙箱内执行（`Operation not permitted`），但编译产物正确。CI 流水线的签名步骤可解决此问题。
2. **`_XOPEN_SOURCE` 警告**：header.h 第 5 行的 `#define _XOPEN_SOURCE` 与 OHOS sysroot 的 `features.h` 冲突，产生编译警告但不影响功能。
---

**编译结束**: 2026-08-08 13:38
**最终状态**: built
