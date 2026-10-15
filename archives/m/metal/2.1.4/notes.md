# metal 2.1.4 适配笔记

## 编译环境
- 构建系统: cmake（头文件库，无编译，仅打包头文件）
- 编译日期: 2026-09-28
- 编译器: clang 15.0.4 / clang++
- 状态: built
- 上游来源: https://github.com/brunocodutra/metal (官方 tag v2.1.4, commit 9db9b403e58e0be0bbd295ff64f01e700965f25d)
- 源码 sha256: 66140e89e424d89bc24bd296884a51487a72c04faf0d0254f3f5950648ffbba1

## 编译步骤

metal 是 C++14 模板元编程头文件库（header-only），无编译产物：
1. init-build 下载官方 v2.1.4 tarball 并解压（构建缓存目录 builds/metal-2.1.4.work）
2. lang-preflight: cpp 匹配（cmake 构建系统，源文件 225 个，cpp 主体占比 99%）
3. conan-init 生成配方骨架 → 重写为 header-only 配方（无 build()，package() 仅拷贝 include/metal.hpp + include/metal/**）
4. test_package: 真实消费者测试 test.cpp（包含 <metal.hpp>，验证 metal::list/size/front/numbers/add 编译期行为）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-init 误用 autotools 模板 | 自动构建系统探测对 header-only 库不准确 | 按 templates/conanfile-headeronly.py.tmpl 重写为 header-only 配方 |
| 2 | 生成 test_package/test.c 仅为 printf 桩 | 模板缺省桩测试不满足 R34 | 删除桩，改为真实调用 metal API 的 test.cpp |
| 3 | 磁盘 inode 耗尽 (ENOSPC) | 共享文件系统 inode 100% | 临时释放知识快照 inode，知识门禁前按同一远端/ref 重建 |

## 源码修改

无（header-only 库，无需打补丁；patches/ 为空）。

## 上游测试

- 上游测试清点: test/ 下 unit / header / formatting / deployment 四个子目录，
  通过 CMake 自定义目标 `tests` 聚合（test.unit / test.header / test.formatting / test.deployment）
- 实际运行: 见 upstream_tests 门禁记录（test_package/MANIFEST.yml）
---

**编译结束**: 2026-09-29 11:11
**最终状态**: built
