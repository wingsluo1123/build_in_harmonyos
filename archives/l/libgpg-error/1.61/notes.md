# libgpg-error 1.61 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-26
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 应用 E011 修复：修改 configure 中的 umask 077 为 umask 022
   ```bash
   sed -i 's/umask 077/umask 022/g' configure
   ```

2. 执行 configure
   ```bash
   ./configure --prefix=$DEFAULT_PREFIX
   ```

3. 编译
   ```bash
   make -j2
   ```

4. 安装到 staging 目录
   ```bash
   make install DESTDIR=$TEST_PREFIX
   ```

5. 安装到系统
   ```bash
   make install
   ```

6. 处理 HMDFS 符号链接问题（用实际文件替代符号链接）
   ```bash
   cd $DEFAULT_PREFIX/lib
   rm -f libgpg-error.so.0 libgpg-error.so
   cp -a libgpg-error.so.0.42.1 libgpg-error.so.0
   cp -a libgpg-error.so.0.42.1 libgpg-error.so
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 失败：Permission denied 创建临时文件 | HMDFS UID 映射 + umask 077 导致临时目录不可写（E011） | 修改 configure 中 umask 077 为 umask 022 |
| 2 | 二进制运行失败：Error loading shared library | HMDFS 不支持符号链接（PSCAN-HMDFS-001） | 用 cp -a 替代 ln -s 创建符号链接 |

## 源码修改

**修改文件：configure**
- 修改原因：解决 E011（HMDFS umask 077 权限问题）
- 修改内容：sed -i 's/umask 077/umask 022/g'
- 知识引用：E011

## 依赖版本

- 无外部依赖（基础库）

## 验证结果

```bash
/storage/Users/currentUser/usr/local/bin/gpg-error --version
gpg-error (libgpg-error) 1.61
Copyright (C) 2025 g10 Code GmbH
License GNU LGPL-2.1-or-later <https://gnu.org/licenses/>
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.
```

## 交付物

暂无打包产物（需要处理符号链接问题后再制作预编译包）

## 注意事项

1. **HMDFS 符号链接问题**：在 HMDFS 文件系统上，符号链接可能不工作，需要用实际文件替代（cp -a）
2. **E011 修复必须应用**：所有 autotools 项目在 HMDFS 上都需要修改 configure 中的 umask 077

---
**编译结束**: 2026-05-26 21:00
**最终状态**: built（编译成功，验证通过）
---

**编译结束**: 2026-05-26 21:00
**最终状态**: built
