# tree-sitter 0.25 适配笔记

## 编译环境
- 构建系统: makefile (plain Makefile, no configure)
- 编译日期: 2026-07-15
- 编译器: clang/clang++ (15.0.4)
- 状态: built

## 编译步骤

1. 下载源码: https://github.com/tree-sitter/tree-sitter/archive/refs/tags/v0.25.0.tar.gz
2. 解压源码
3. `make CC=clang -j1` — 编译 libtree-sitter.a 和 libtree-sitter.so
4. `make install PREFIX=/usr/local DESTDIR=$TEST_PREFIX` — 安装到 staging 目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create: No targets specified and no makefile found | Conan build() runs from build_folder, not source_folder | 使用 `make -C {self.source_folder}` 指定源码目录 |
| 2 | conan create: tools.build:compiler_executables:c does not exist | Conan 2.29.1 不支持子键访问 | 改用 `self.conf.get("tools.build:compiler_executables", check_type=dict)` 获取 dict |
| 3 | test.c 空壳测试 | 模板生成的 test.c 只打印字符串 | 改写为调用 ts_parser_new()/ts_parser_delete() 实质测试 |

## 源码修改

无补丁，无需修改源码。

## 依赖版本

无外部依赖（仅依赖 libc）。

## 验证结果

```bash
conan create 通过 (G1-G4 全部 PASS)
readelf -d libtree-sitter.so → NEEDED: libc.so (无额外依赖)
```

## 注意事项

- tree-sitter 上游测试套件需要 Rust/cargo 环境 (cargo xtask test)，OHOS 平台跳过
- test_package 使用 C API ts_parser_new() 进行消费者视角验证
- 库类型: library (非命令行工具，不需要 commands.json)
## 二次校准 (2026-07-17)

### 问题
CI 报告 "Conan test_package: 失败"，但整体 CI 通过（非阻塞）。

### 根因
test_package 的 `test()` 方法使用 `cmake.test()`，该方法调用 `cmake --build --target test -- -j20`。
在 OHOS 平台上，make 的 jobserver 会尝试在 /tmp 创建 FIFO，导致 `make: jobserver mkfifo: Operation not permitted` 错误。
虽然测试本身通过，但 make 的退出码可能导致 Conan 报告 test_package 失败。

### 修复
将 `test()` 方法从 `cmake.test()` 改为直接 `self.run()` 运行测试二进制文件，
绕过 CTest/make jobserver 机制，避免 OHOS 平台的 FIFO 权限问题。

---

**编译结束**: 2026-07-15 23:15
**二次校准**: 2026-07-17
**最终状态**: built
