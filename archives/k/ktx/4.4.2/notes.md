# ktx 4.4.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-29
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 使用 `ohc-run.py init-build ktx 4.4.2` 下载源码并初始化构建环境
2. 使用 CMake 构建系统，通过 `CMakeToolchain` 注入平台适配选项
3. 禁用不适用的平台特性（VK/GL 上传、JNI、Python、文档、工具、测试）
4. 设置 `CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY` 避免 OHOS 交叉编译 try-link 失败
5. `cmake.configure()` → `cmake.build()` → `cmake.install()`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS 平台无 Vulkan/OpenGL 库 | OHOS 未提供 Vulkan/OpenGL SDK | 关闭 `KTX_FEATURE_VK_UPLOAD` 和 `KTX_FEATURE_GL_UPLOAD` |
| 2 | CMake try-link 失败 | 交叉编译无法执行目标平台二进制 | 设置 `CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY` |

## VK/GL 上传功能关闭决策

KTX-Software 属于图形/渲染领域三方库（R40 覆盖范围），其核心功能涉及 Vulkan/OpenGL 纹理上传。
当前适配**仅覆盖纹理容器的读写功能**（KTX2 格式的创建、读取、写入等内存数据结构操作），
关闭了以下平台相关特性：

- `KTX_FEATURE_VK_UPLOAD=OFF` — Vulkan 纹理上传（OHOS 无 Vulkan SDK）
- `KTX_FEATURE_GL_UPLOAD=OFF` — OpenGL 纹理上传（OHOS 无 OpenGL SDK）
- `KTX_FEATURE_JNI=OFF` — Java JNI 绑定
- `KTX_FEATURE_PY=OFF` — Python 绑定
- `KTX_FEATURE_DOC=OFF` — 文档生成
- `KTX_FEATURE_TESTS=OFF` — 上游测试程序
- `KTX_FEATURE_TOOLS=OFF` — 命令行工具

**影响范围**：库在鸿蒙上仅支持 KTX/KTX2 纹理容器的内存读写，无法与图形栈交互上传纹理。
若后续需要完整图形栈支持，需为 VK_UPLOAD / GL_UPLOAD 添加鸿蒙适配补丁。

## 源码修改

无补丁，通过 CMake 缓存变量控制编译选项。

## 依赖版本

无外部依赖。

## 验证结果

```bash
# conan create 成功，test_package 通过
# test_ktx 验证 ktxErrorString API 和 ktxTexture2_Create 纹理创建
```

---

**编译结束**: 2026-07-29 16:45
**最终状态**: built
