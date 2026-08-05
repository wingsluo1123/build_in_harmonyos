# aws-c-http 0.10.14 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-05
- 编译器: clang
- 状态: built (conan create + conan-verify 通过)

## 编译步骤
使用标准 CMake + Conan 流程：
```bash
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

## 依赖版本
- aws-c-common 0.12.6
- aws-c-io 0.26.3 (使用 BYO_CRYPTO=ON 禁用 s2n-tls)
- aws-c-compression 0.3.2
- aws-c-cal 0.9.13 (aws-c-io 的传递依赖，aws-c-http 直接引用 aws/cal/hash.h)

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | aws/cal/hash.h not found | CMakeDeps 不传播 aws-c-cal 的 include dirs | 1. 添加 aws-c-cal 为直接依赖 2. 在 build() 中手动添加 -I 标志 |
| 2 | aws_http_library_init(NULL) 崩溃 | 函数要求非 NULL allocator | 使用 aws_default_allocator() 获取分配器 |
| 3 | aws-c-io 需要 s2n-tls | 默认 TLS 实现依赖 s2n | BYO_CRYPTO=ON 禁用 |
| 4 | aws-c-io 平台检测 | CMAKE_SYSTEM_NAME=HarmonyOS 不匹配 Linux | 设置 CMAKE_SYSTEM_NAME=Linux |

## 注意事项
- aws-c-http 的 websocket_bootstrap.c 直接引用 aws/cal/hash.h（来自 aws-c-cal）
- conan recipe 中需要将 aws-c-cal 声明为直接依赖
- 所有 AWS C 库使用 aws_use_package() 宏，需要 CMakeDeps 设置 cmake_target_name 为 AWS:: 前缀
---

**编译结束**: 2026-08-06 00:41
**最终状态**: built
