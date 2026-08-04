# aws-c-event-stream 0.7.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-05
- 编译器: clang 15.0.4
- 状态: built (conan-verify passed)

## 编译步骤

使用标准 CMake 流程（通过 Conan 管理）：
```bash
conan create . -pr:b=ohos-aarch64 -pr:h=ohos-aarch64
```

关键 CMake 选项：
- `-DBUILD_SHARED_LIBS=OFF` 静态库
- `-DBUILD_TESTING=OFF` 禁用测试
- `-DBYO_CRYPTO=ON` 跳过 s2n TLS 依赖
- `CMAKE_PREFIX_PATH` 指向所有依赖的 conan 包目录

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | aws-c-io cmake config 调用 find_dependency(s2n) | aws-c-io 默认启用 s2n TLS | 设置 BYO_CRYPTO=ON 跳过 s2n 依赖 |
| 2 | aws-checksums targets 引用 aws-c-common::aws-c-common 但目标不存在 | aws-checksums 使用 CMakeDeps 构建，记录 conan 命名空间目标 | 创建 ALIAS 目标 patch: aws-c-common::aws-c-common → AWS::aws-c-common |
| 3 | CMAKE_PREFIX_PATH 需包含所有传递依赖 | aws-c-io cmake config 调用 find_dependency(aws-c-cal) | 将 aws-c-cal 包目录加入 CMAKE_PREFIX_PATH |

## 依赖版本
- aws-c-common/0.12.6
- aws-c-cal/0.9.13
- aws-c-io/0.26.3
- aws-checksums/0.2.10

## 注意事项
- aws-c-event-stream 不直接依赖 aws-c-http（CMakeLists.txt 中无引用）
- CMAKE_SYSTEM_NAME 由 conan 工具链设置为 HarmonyOS，不影响构建
- BYO_CRYPTO=ON 在 aws-c-event-stream 中需要设置，因为 aws-c-io 的 cmake config 检查此变量
---

**编译结束**: 2026-08-05 05:17
**最终状态**: built
