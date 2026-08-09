# aws-c-io 0.26.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-05
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤
```bash
cmake -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DBYO_CRYPTO=ON \
  -DBUILD_SHARED_LIBS=OFF \
  -DBUILD_TESTING=OFF
cmake --build build -j$(nproc)
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | s2n 依赖缺失 | 默认需要 s2n-tls | `-DBYO_CRYPTO=ON` 禁用 |
| 2 | Event Loop 不匹配平台 | CMakeLists.txt 不识别 HarmonyOS | 补丁添加 HarmonyOS 到 Linux 平台检查 |

## 依赖版本
- aws-c-common 0.12.6
- aws-c-cal 0.9.13 (依赖 aws-lc 5.4.0)

## 注意事项
- BYO_CRYPTO=ON 禁用 TLS，不影响基本 IO
- 编译产物: libaws-c-io.a
- CMakeDeps 不自动生成 aws-c-common 的 include dirs，test_package 显式 requires aws-c-common
---

**编译结束**: 2026-08-05 05:13
**最终状态**: built
