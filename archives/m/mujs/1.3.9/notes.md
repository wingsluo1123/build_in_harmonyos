# mujs 1.3.9 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-07-15
- 编译器: clang/clang++
- 状态: built

## 编译步骤

mujs 使用简单的 Makefile 构建，无 configure 脚本。

```bash
# 编译
make release HAVE_READLINE=no -j1

# 安装（staging）
make install HAVE_READLINE=no prefix=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX
make install-shared HAVE_READLINE=no prefix=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | print 未定义 | MuJS API 不包含 print 函数，仅 CLI 注册 | 在 test.c 中注册 jsB_print 函数 |
| 2 | conan build 目录不匹配 | basic_layout 创建 build-release 子目录 | 使用 make -C 指定源码目录 |

## 依赖版本

无外部依赖。

## 验证结果

```bash
$ mujs test_mujs.js
Hello from MuJS! 6
```

## 注意事项

- readline 支持已禁用（HAVE_READLINE=no），因系统缺少 readline 库
- 构建产物包含静态库、动态库和两个可执行文件（mujs, mujs-pp）

编译结束
