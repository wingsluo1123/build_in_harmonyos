# popt 1.19 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-15
- 编译器: clang 15.0.4
- 状态: published

## 编译步骤

1. 下载源码: https://ftp.osuosl.org/pub/rpm/popt/releases/popt-1.x/popt-1.19.tar.gz
2. 替换 config.guess/config.sub 为 autoconf 2.72 版本并打 OHOS 补丁 (E007)
3. 修复 configure 脚本中 umask 077 → umask 022 (HarmonyOS 权限兼容)
4. 创建 `print` 命令包装器 (ksh `print -r --` 兼容)
5. `./configure --prefix=$DEFAULT_PREFIX`
6. `make -j1`
7. `make install DESTDIR=$TEST_PREFIX` (staging)
8. `make check` — 1/1 PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识别 HarmonyOS | 2018-08-29 版本不含 OHOS 检测 (E007) | 替换为 autoconf 2.72 版本 + patch-autotools-ohos.pl + 手动添加 linux-ohos 内核-OS 组合 |
| 2 | config.status: Permission denied | umask 077 创建 drwx------ 目录，UID 不匹配 (20020102 vs 20001006) | 补丁: umask 077 → umask 022 |
| 3 | config.status: print: command not found | configure 检测到 ksh `print` 命令，但 bash 无此内置命令 | 创建 `print` 包装器脚本到 ~/usr/local/bin |
| 4 | make: jobserver mkfifo 失败 | HarmonyOS 不支持 mkfifo (FIFO) | 使用 make -j1 |
| 5 | make: aclocal-1.16 缺失 | automake 未安装，Makefile 尝试重新生成 | touch 时间戳阻止重新生成 |

## 源码修改

| 文件 | 补丁 | 说明 |
|------|------|------|
| build-aux/config.guess | 0001-build-aux-config.guess.patch | 替换为 autoconf 2.72 版本 + OHOS 平台检测 |
| build-aux/config.sub | 0002-build-aux-config.sub.patch | 替换为 autoconf 2.72 版本 + OHOS 三元组支持 |
| configure | 0003-configure.patch | umask 077 → umask 022 |

## 依赖版本

无外部依赖。popt 是独立的 C 库。

## 验证结果

```
conan create popt/1.19 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
→ G1 PASS, G2 PASS (conan create), G3 PASS, G4 PASS
→ 配方验证通过，可标记 status: published
```

## 交付物

| 文件 | 说明 |
|------|------|
| libpopt.so.0.0.2 | 共享库 |
| libpopt.a | 静态库 |
| popt.h | 头文件 |
| popt.pc | pkg-config 元数据 |

## 注意事项

- CI 环境需要 `print` 命令可用（或 configure 使用 printf 替代）
- `umask 022` 补丁在 CI 中也可能需要（取决于 CI worker 的 UID/GID 配置）
- `make -j1` 是必须的（HarmonyOS 不支持 mkfifo）
---

**编译结束**: 2026-07-15 21:51
**最终状态**: published
