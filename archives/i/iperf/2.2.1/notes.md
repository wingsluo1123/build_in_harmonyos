# iperf 2.2.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-06
- 编译器: clang/clang++
- 状态: built → conan adapted

## 编译步骤

1. 从 SourceForge 下载源码 tarball (sha256: 754ab0a7e28033dbea81308ef424bc7df4d6e2fe31b60cc536b61b51fefbd8fb)
2. 应用 config.guess/config.sub 补丁（OHOS 平台识别）
3. 修改 headers.h（解决 linux/socket.h 与 sys/socket.h 冲突）
4. 修改 checksums.c（适配 musl udphdr 结构体）
5. configure --prefix=$DEFAULT_PREFIX
6. make -j2
7. make install DESTDIR=$TEST_PREFIX
8. make check (16/16 fail: /bin/bash not found on HarmonyOS)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 补丁缺少 exit 语句 | 添加 echo "$GUESS" && exit ;; |
| 2 | config.sub 报错 "Kernel 'linux' not known to work with OS 'ohos'" | linux-ohos 组合未添加到验证列表 | 添加 linux-ohos* 到 kernel-os 验证 |
| 3 | sockaddr_storage 重复定义 | linux/tcp.h 包含 linux/socket.h 与 sys/socket.h 冲突 | 使用宏别名 #define sockaddr_storage sockaddr_storage_ohos_alias |
| 4 | udphdr.check 成员不存在 | musl libc 使用 uh_sum 命名 | 添加 #ifdef __OHOS__ 条件编译 |
| 5 | config.status: could not setup config files machinery | umask 077 creates temp dirs owned by wrong user (20001006 vs 20020101) with 700 perms | conanfile.py build() replaces umask 077 with umask 022 |
| 6 | make check: 16/16 tests fail | test scripts use #!/bin/bash which doesn't exist on HarmonyOS | Platform limitation, not a code issue |

## Conan 适配

- 软件类型: application (CLI tool, not library)
- 构建系统: autotools
- 无外部依赖
- test_package: 运行 iperf --version 验证二进制
- commands.json: 已创建 (R38)
- 补丁: 4 个 (config.guess, config.sub, headers.h, checksums.c)

## 源码修改

- config.guess: 添加 HarmonyOS 识别 + exit 语句
- config.sub: 修复 ohos-linux 格式 + 添加 linux-ohos* 验证
- include/headers.h: OHOS 头文件冲突解决方案
- src/checksums.c: musl udphdr 适配
- configure (build-time fix, not patch): umask 077 → umask 022 in build() method

## 验证结果

```bash
$ iperf --version
iperf version 2.2.1 (4 Nov 2024) pthreads
```
---

**编译结束**: 2026-08-06 20:34
**最终状态**: published
