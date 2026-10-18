# wf-utils 0.4.0 适配笔记

## 编译环境
- 构建系统: meson (meson_version >= 0.50)
- 编译日期: 2026-10-17
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos) / clang++
- 状态: published

## 编译步骤
1. 获取源码：wayfire v0.10.0 submodule 引用 commit 3ef27d1f76b5f3d1f34305bff12b3174e81727c2（无正式 release tag）
2. meson 交叉编译（OHOS aarch64 profile）
3. conan create 完整验证通过，test_package 鸿蒙冒烟测试 1/1 Passed

## 上游测试（R51 申报表）
- **上游无独立测试**：清点确认 wf-utils 上游 meson.build 未注册任何 test（`#subdir('test')` 注释状态），
  `wayfire/condition/test_condition.cpp` 为库功能源码（test_condition_t 类实现，非测试可执行）。
  源码 32 个 .cpp 均属库功能，无 tests/ 目录、无 doctest/ctest 注册。
- 通过率：不适用（上游无测试用例，附清点证据如上）

## 源码修改
无（纯构建适配）

## 依赖版本
无外部依赖

## 验证结果
```bash
# conan create（主包 + test_package）
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 ...   # PASS
# test_package 鸿蒙冒烟
1/1 test_wfutils OK  (wf-utils smoke test OK: variant_t, is_int/is_string/is_bool)
# 上游测试：无注册用例（清点确认）
```
