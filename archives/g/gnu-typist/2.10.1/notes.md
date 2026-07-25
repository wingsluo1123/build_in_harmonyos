# gnu-typist 2.10.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-18
- 编译器: OHOS clang 15（通过 profile ci/conan/profiles/ohos-aarch64 指定）
- 状态: built

## 编译步骤
1. `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64`
2. Autotools 构建流程：./configure → make → make install
3. 额外参数：--disable-nls（禁用 gettext NLS），--enable-static/--disable-shared
4. test_package 执行 gtypist --version 验证二进制可执行

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 脚本 mktemp -d 在 HMDFS 上失败 | HMDFS 不支持在 mktemp -d 创建的临时目录中写入文件 | 用 mktemp -p + rm + mkdir 方式替代，使用局部变量 `t` 捕获路径 |
| 2 | getopt.c 编译错误 0→NULL 类型转换 | 旧版 getopt 实现使用 `0` 作为空指针，clang 15 C99 严格模式报错 | 添加 -Wno-int-conversion 编译标志抑制 |
| 3 | gettext 未定义链接错误 | OHOS libc 不提供 gettext 函数 | 定义 gettext_stub.h 通过 -include 注入空实现 |
| 4 | help2man 缺失 | OHOS 环境没有 help2man | 创建 help2man wrapper 脚本（exit 0） |

## 源码修改
采用内联方式处理，不维护外部补丁文件：
- 在 build() 中替换 configure 脚本的 mktemp 行为
- 在 generate() 中添加编译标志 -Wno-int-conversion 和 gettext stub

## 依赖版本
无第三方 Conan 依赖。系统依赖：OHOS SDK clang 15 + libncurses.so.6（OHOS SDK 自带）。

## 验证结果

```bash
$ gtypist --version
GNU Typist 2.10.1
Copyright (C) 2021, 2022, 2023, 2024, 2025 Felix Natter, Mihai Gătejescu
Created by Simon Baldwin
License GPLv3+: GNU GPL version 3 or later
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.
```

## 交付物
- conanfile.py（Conan 配方）
- conandata.yml（源码地址与哈希）
- manifest.yaml（构建元数据）
- test_package/（测试包：conanfile.py + MANIFEST.yml）

## 注意事项
- ncurses 为 OHOS SDK 系统库，不需要额外适配
- gettext NLS 已通过 --disable-nls 禁用，不需要 libintl
- 本适配为路径 A（基础适配），无需知识库新增
---

**编译结束**: 2026-07-25 21:56
**最终状态**: built
