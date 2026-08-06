# gsm 1.0.22 适配笔记

## 编译环境
- 构建系统: Makefile
- 编译日期: 2026-08-06
- 编译器: clang (LLVM)
- 状态: published (conan adapted, CI upload pending)

## 编译步骤
1. 下载 gsm-1.0.22.tar.gz 并解压
2. 应用补丁 0001-makefile-clang-ln-s.patch：
   - CC=gcc → CC=clang
   - CCFLAGS 添加 -fPIC
   - LN=ln → LN=ln -s (HMDFS 兼容)
3. `make CC=clang -j1`
4. 产物：lib/libgsm.a, bin/toast, bin/tcat, bin/untoast, inc/gsm.h

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 使用 gcc | HM 无 gcc | 修改 CC=clang |
| 2 | 缺少 -fPIC | 静态库需位置无关代码 | CCFLAGS 添加 -fPIC |
| 3 | 硬链接失败 | HMDFS 不支持硬链接 | LN=ln -s |

## 依赖版本
- 无依赖

## Conan 适配
- conanfile.py: Makefile 构建系统
- conandata.yml: 源码 SHA256 + 补丁声明
- test_package/: GSM 编解码回环测试 (encode → decode → 验证幅值)
- 构建产物包含可执行文件 (toast/tcat/untoast)，已声明 commands.json

## 注意事项
- 源码 tarball 解压目录为 gsm-1.0-pl22/ (非 gsm-1.0.22/)，conanfile.py 使用 strip_root=True
---

**编译结束**: 2026-08-06 15:53
**最终状态**: published
