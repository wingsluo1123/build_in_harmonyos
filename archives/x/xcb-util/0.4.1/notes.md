# xcb-util 0.4.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-09
- 编译器: clang/clang++
- 状态: published

## 编译步骤

使用 x.org 官方 release tarball（包含预生成 configure 和 m4 宏），通过 Conan 配方自动完成：
1. 下载 release tarball 并解压
2. configure --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu
3. make && make check
4. make install

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | xcbproto_version 变量缺失 | Conan PkgConfigDeps 生成的 xcb.pc 缺少自定义变量 | 从 libxcb 包原始 xcb.pc 复制 xcbproto_version |
| 2 | .la 依赖路径失效 | libtool .la 文件中的 dependency_libs 引用构建时路径 | 修复 libdir 并将 .la 引用替换为 -l 标志 |

## 源码修改

无补丁。使用官方 release tarball。

## 依赖版本

- libxcb/1.17.0
- xorgproto/2025.1

## 验证结果

```bash
$ conan create archives/x/xcb-util/0.4.1/conanfile.py --name xcb-util --version 0.4.1 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# 编译成功，test_package 测试通过
xcb-util api smoke ok
```

## 注意事项

- xcb-util 是 xcb-util-image 和 xcb-util-renderutil 的依赖
- 需要发布到制品仓后下游才能使用

---

**编译结束**: 2026-08-09 01:24
**最终状态**: published
