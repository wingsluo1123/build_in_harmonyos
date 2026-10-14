# unscd 0.54 适配笔记

## 编译环境

- 构建系统: makefile
- 编译日期: 2026-10-13
- 编译器: clang/clang++
- 状态: built

## 上游信息

- 上游作者页: https://busybox.net/~vda/unscd/
- Debian 源码包: unscd_0.54.orig.tar.gz
- SHA256: 823430b97de9349c73f12a33e4c28a9425b3166a77f7e9e03aeccb4964aaee53
- 源码结构: 单个 nscd-0.54.c 文件（73304 字节）+ 223 字节 Makefile（仅 all/clean 目标）
- 许可证: GPL-2.0-only
- 依赖: 无（仅标准 libc 头文件）

## 编译步骤

Debian orig 归档经 conan `get` 解包后，在源码目录执行：

```bash
make CC=<conan-conf-编译器> CFLAGS="-Wall -Os" -j1
```

说明：

- `CC` 来自 Conan conf（`tools.build:compiler_executables`），不依赖 shell 环境变量（R33）。
- 上游 Makefile 默认 CFLAGS 带有 GNU ld 专用选项（`-Wl,--sort-section -Wl,alignment -Wl,--sort-common`），命令行覆盖 `CFLAGS="-Wall -Os"` 以适配 OHOS clang/lld。
- 始终 `-j1`（R9）。
- 上游构建产物名为 `nscd`；打包时复制为 `bin/unscd` 与 `bin/nscd` 两个真实文件（HMDFS 符号链接受限，不用 symlink）。

## 上游测试审计

上游 0.54 不存在自动化测试套件：

- 无 tests/、test/、spec/、t/ 目录。
- Makefile 无 check/test 目标（`make -n check` 报告无此规则）。
- 源码无 gtest/pytest 用例。
- 仅有的 getpwnam_test.c（188 字节）是手动 NSS 探针，不是可运行套件。

因此 `test_package/MANIFEST.yml` 按 `upstream_tests_exist: false` + `upstream_test_total: 0` 申报，
`build()` 与 `test()` 输出 `status: no_tests` 的机器证据标记。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游无测试套件可接入 | 单文件守护进程，无自动化测试 | test_package 做 4 项消费者验证：二进制存在、`-V` 版本输出、`--help` 用法输出、NSS 消费者程序 |
| 2 | 上游默认 CFLAGS 含 GNU ld 专用选项 | 为 glibc/GNU ld 编写 | make 命令行覆盖 CFLAGS |
| 3 | 上游产物名与包名不一致 | 上游构建出 `nscd` | 打包同时提供 `unscd` 与 `nscd` |
| 4 | OHOS clang/lld 报 `undefined symbol: __nss_disable_nscd` | `nscd-0.54.c` 无条件声明+调用 glibc 内部函数 `__nss_disable_nscd`，OHOS/musl libc 无此符号 | `build()` 内幂等改写：声明加 `__attribute__((weak))`，调用改为 `if (__nss_disable_nscd)` 守卫；glibc 仍正常调用，非 glibc 安全跳过，无平台宏 |

## 依赖版本

无运行时依赖。

## 验证结果

```bash
bash test_package/test.sh
# 4/4 检查通过：二进制存在、`unscd -V` 含 0.54、`--help` 含 Usage: nscd、NSS 消费者程序退出 0
```

## 注意事项

- `unscd --help` 按上游设计退出码为 1，测试只校验输出内容，不校验退出码。
- NSS 消费者检查中“用户不存在”视为通过（断言的是 API 调用本身可用，而非特定用户存在）。
