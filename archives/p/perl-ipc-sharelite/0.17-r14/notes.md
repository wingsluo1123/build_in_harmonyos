# perl-ipc-sharelite 0.17-r14 适配笔记

## 编译环境
- 构建系统: Perl XS (ExtUtils::MakeMaker)
- 编译日期: 2026-08-07
- 编译器: clang/clang++ (at /data/service/hnp/bin/)
- 状态: published

## 编译步骤

```bash
cd ~/tmp/builds/perl-ipc-sharelite-0.17-r14.work
perl Makefile.PL
make -j1
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 历史补丁硬编码 musl 路径 | 旧版 clang 无 musl 头文件路径 | 使用 /data/service/hnp/bin/clang 后无需补丁 |
| 2 | 历史补丁修改 LDDLFLAGS | 旧版链接器无 crt*.o 路径 | 使用 /data/service/hnp/bin/clang 后链接器自动找到 CRT |

## 产物

| 文件 | 路径 | 说明 |
|------|------|------|
| ShareLite.so | blib/arch/auto/IPC/ShareLite/ | XS 共享库 (ELF, 依赖 libc.so) |
| ShareLite.pm | blib/lib/IPC/ | Perl 模块源码 |
| autosplit.ix | blib/lib/auto/IPC/ShareLite/ | AutoSplit 索引 |

## 注意事项

1. **无需补丁**: 使用 /data/service/hnp/bin/clang 编译器时, Makefile.PL 生成的 Makefile 已包含正确的编译参数
2. **SysV IPC 依赖**: 目标系统需支持共享内存和信号量 (shmget/semget 等)
3. **SELinux HMDFS 限制**: 用户目录上的 .so 无法 dlopen, 需管理员安装到 /data/service/hnp/

---
**编译结束**: 2026-08-07
**最终状态**: published
