# libgit2

libgit2 是一个跨平台的、可链接的 Git 库实现，提供 Git 核心功能的 C API。

## 描述

libgit2 是一个轻量级、纯 C 实现的 Git 核心方法库，支持：
- Git 仓库操作（初始化、克隆、打开）
- 提交、分支、标签管理
- 远程仓库交互（fetch、push）
- 索引和工作目录操作
- diff、merge、rebase 等高级操作
- HTTPS 和 SSH 传输支持

## 版本

- 1.9.4 (2025-05-27)

## 依赖

- openssl (HTTPS 支持)
- zlib (压缩)
- cmake (构建工具)

## 编译选项

```
cmake -B build -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local -DBUILD_TESTS=ON
cmake --build build -j2
cmake --install build --prefix /storage/Users/currentUser/usr/local
```

## 验证

```bash
/storage/Users/currentUser/usr/local/bin/git2 --version
```

## 许可证

GPLv2 with linking exception
