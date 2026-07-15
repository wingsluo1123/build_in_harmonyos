# nkf 2.1.5 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-07-15
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码: nkf_2.1.5.orig.tar.gz (Debian 官方源)
2. 应用补丁: 0001-Makefile.patch (修改 man 页安装路径)
3. 编译: `make CC=clang CFLAGS="-fPIC -O2 -Wall"`
4. 安装: `make install prefix=$TEST_PREFIX MKDIR="mkdir -p"`
5. 测试: `make test` (Perl 测试套件)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | man 页安装到 prefix/man 而非标准路径 | Makefile 硬编码 man 路径 | 补丁修改为 prefix/share/man |
| 2 | conan create 中 make 报 "unknown output-sync type" | CFLAGS 未加引号，make 将 -O2 解析为 --output-sync=2 | 在 conanfile.py 中对 CFLAGS 加双引号 |
| 3 | conan create 中 make 找不到 Makefile | basic_layout 将构建目录设为 build-release 子目录 | 改为手动设置 layout，build 在源码根目录 |

## 源码修改

- 0001-Makefile.patch: 修改 Makefile 中 man 页安装路径从 prefix/man 到 prefix/share/man

## 依赖版本

无外部依赖。nkf 是纯 C 程序，仅依赖标准库。

## 验证结果

```bash
$ make test
All tests are succeeded.
# ~120 个编码转换测试全部通过
```

## 注意事项

- nkf 是命令行工具，不是库
- 使用 Perl 测试套件 (test.pl) 进行验证
- 无外部依赖，纯 C 编译
- conanfile.py 中 CFLAGS 需加引号防止 make 误解析

**编译结束**: 2026-07-15
**最终状态**: built
