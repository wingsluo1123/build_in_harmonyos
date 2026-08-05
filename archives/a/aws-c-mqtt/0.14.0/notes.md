# aws-c-mqtt 0.14.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-05
- 编译器: clang
- 状态: built (conan create 验证通过)

## 编译步骤
标准 CMake 构建，使用 Conan 管理依赖链。

### 依赖链
aws-c-mqtt/0.14.0
├── aws-c-common/0.12.6 (已适配，conan create 通过)
├── aws-c-http/0.10.14 (本次适配，conan create 通过)
│   ├── aws-c-io/0.26.3 (本次适配，conan create 通过)
│   │   ├── aws-c-cal/0.9.13 (已适配，conan create 通过)
│   │   │   ├── aws-c-common/0.12.6
│   │   │   └── aws-lc/5.4.0 (已适配，conan create 通过)
│   │   └── aws-c-compression/0.3.2 (本次适配，conan create 通过)
│   ├── aws-c-compression/0.3.2
│   └── aws-c-cal/0.9.13
├── aws-c-io/0.26.3
├── aws-c-cal/0.9.13
└── aws-c-compression/0.3.2

### 关键适配点
1. aws-c-io/0.26.3 需要 HarmonyOS 平台补丁（CMakeLists.txt 中添加 HarmonyOS 到 Linux 分支，启用 epoll 事件循环）
2. aws-c-io/0.26.3 设置 BYO_CRYPTO=ON 避免 s2n-tls 依赖
3. aws-c-http/0.10.14 需要声明 aws-c-cal 为直接依赖（源码直接 include aws/cal/hash.h）
4. aws-c-mqtt/0.14.0 声明所有直接和传递依赖，确保 CMakeDeps 正确生成 find_package 配置
5. CMakeDeps 设置 cmake_target_name 为 AWS::xxx 以匹配 AWS C 库的 CMake 模块约定
6. CMAKE_MODULE_PATH 需要指向 aws-c-common 的 modules 目录（AwsCFlags, AwsFindPackage 等）

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | aws-c-io 编译失败: "Event Loop is not setup on the platform" | CMakeLists.txt 未识别 HarmonyOS 平台 | 添加 HarmonyOS 到 Linux 平台分支 |
| 2 | aws-c-http 编译失败: aws/cal/hash.h not found | aws-c-cal 未声明为直接依赖 | 添加 aws-c-cal 到 requirements 和 CMakeDeps |
| 3 | aws-c-http 测试失败: allocator != NULL | aws_http_library_init 要求非 NULL allocator | 使用 aws_default_allocator() 获取默认分配器 |
| 4 | GitHub 源码下载超时 | HarmonyOS 设备无法直接访问 GitHub | 使用 ghfast.top 镜像代理 |
---

**编译结束**: 2026-08-06 00:24
**最终状态**: built
