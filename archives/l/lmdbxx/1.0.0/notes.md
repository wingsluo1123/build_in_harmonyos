# lmdbxx 1.0.0 适配笔记

## 编译环境
- 构建系统: makefile (header-only library)
- 编译日期: 2026-07-15
- 编译器: clang/clang++
- 状态: built

## 软件简介

lmdbxx 是 LMDB 数据库的 C++17 封装库，提供 RAII 风格的 C++ 接口。
这是一个 header-only 库，只提供一个头文件 `lmdb++.h`（44175 字节）。

## 编译步骤

### 1. 下载源码
- 从 GitHub 下载: https://github.com/hoytech/lmdbxx/archive/refs/tags/1.0.0.tar.gz
- SHA256: 629912b64c71d4e7f3eaa6265f83e36169806f45874b0600ca924d2ed6c677f2

### 2. 安装头文件
lmdbxx 是 header-only 库，只需安装 `lmdb++.h`：
```bash
make install PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX
make install PREFIX=$DEFAULT_PREFIX
```

### 3. 运行上游测试
```bash
# 需要 lmdb 库（lmdb.h + liblmdb.so）
make check CPPFLAGS="-I$HOME/usr/local/include" LDFLAGS="-L$HOME/usr/local/lib"
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `lmdb.h` not found | Makefile 的 CPPFLAGS 只包含 `-I.`，不搜索系统头文件路径 | 添加 `-I$HOME/usr/local/include` 到 CPPFLAGS |
| 2 | `./version:1:1: error: expected unqualified-id` | 源码目录中有 `version` 文件，与 C++17 标准 `<version>` 头文件冲突 | 从 CPPFLAGS 中移除 `-I.`，check.cc 使用 `#include "lmdb++.h"`（引号）仍能找到本地头文件 |

## 依赖说明

- **lmdb/0.9.32** (conancenter): lmdbxx 的 `lmdb++.h` 包含 `<lmdb.h>`，编译和测试时需要 lmdb 的头文件和库
  - 从 cmd-pkgs 安装了 lmdb 0.9.35 用于本地测试
  - conan 配方中声明 `self.requires("lmdb/0.9.32")`
  - lmdb 尚未发布到 ohpcd 制品仓，本地 conan create 使用 conancenter

## 源码修改

无补丁。lmdbxx 是纯 header-only 库，无需修改源码即可在鸿蒙平台使用。

## 验证结果

```bash
# 头文件安装验证
ls -la $DEFAULT_PREFIX/include/lmdb++.h
# 输出: -rw-rw---- 1 20001006 file_manager 44175 2026-07-15 18:19 lmdb++.h

# 上游测试
make check CPPFLAGS="-I$HOME/usr/local/include" LDFLAGS="-L$HOME/usr/local/lib"
# 编译成功，测试通过（无输出表示成功）
```

## 注意事项

1. **Header-only 库特性**
   - lmdbxx 只提供一个头文件 lmdb++.h
   - 无需编译，直接安装到 include 目录即可
   - 使用时需 `#include <lmdb++.h>` 并链接 LMDB 库

2. **C++17 要求**
   - lmdbxx 1.0.0 要求 C++17（`#if __cplusplus < 201703L` 会报错）
   - conan profile 的 compiler.cppstd=17 满足要求

3. **lmdb 依赖**
   - lmdbxx 需要 lmdb 库（lmdb.h 和 liblmdb.so）
   - 编译时需要 lmdb.h 头文件
   - 运行时需要 liblmdb.so 库
   - lmdb 可从 cmd-pkgs 安装（0.9.33/0.9.35）或从 conancenter 获取（0.9.29/0.9.31/0.9.32）

---
---

**编译结束**: 2026-07-15 18:30
**最终状态**: built
