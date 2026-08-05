# bear 3.1.6 适配笔记

## 编译环境
- 构建系统: cmake (superbuild with ExternalProject_Add)
- 编译日期: 2026-08-05
- 编译器: clang/clang++ 15.0.4
- 状态: built (Conan recipe verified)

## 编译步骤
Bear 使用 CMake superbuild 方式构建，所有依赖通过 ExternalProject_Add 从源码编译：
1. nlohmann_json v3.11.3 (header-only)
2. fmt v11.0.2
3. spdlog v1.14.1
4. gRPC v1.49.2 (含 abseil, protobuf, boringssl, re2, c-ares, zlib)
5. BearSource (bear 主程序)

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | source/CMakeLists.txt VERSION 引用 ${CMAKE_PROJECT_VERSION} 在 ExternalProject 中不可用 | ExternalProject_Add 不传递 CMAKE_PROJECT_VERSION | 补丁 0001: 硬编码 VERSION 3.1.6 |
| 2 | gRPC v1.49.2 tarball 不含 git submodules | GitHub tarball 不包含 submodule 内容 | 补丁 0002+0005: fetch_submodules.sh 脚本下载各 submodule |
| 3 | boringssl CMakeLists.txt 检测 CMAKE_SYSTEM_PROCESSOR 为 "unknown" | HarmonyOS 未被 CMake 识别 | 补丁 0006: patch_boringssl.py 添加 aarch64 fallback |
| 4 | boringssl 尝试使用 ASM_NASM (Windows assembler) | HarmonyOS 不被识别为 UNIX | 补丁 0006: 添加 HarmonyOS 到 UNIX 检查 |
| 5 | boringssl ASM 符号缺失 (aes_hw_*, gcm_ghash_neon 等) | aarch64 ASM 文件未正确编译 | 设置 OPENSSL_NO_ASM=ON 使用 C 实现 |
| 6 | c-ares CMakeLists.txt 需要兼容旧版 CMake | CMake 4.x 移除了 < 3.5 兼容 | 设置 CMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 7 | BearSource pkg_check_modules 找不到 gRPC | gRPC .pc 文件依赖 openssl.pc 不存在 | 补丁 0003: 改用 find_package(gRPC CONFIG) |
| 8 | BearSource 找不到 protoc/grpc_cpp_plugin | gRPC 安装在非系统路径 | 补丁 0004: 添加 gRPC_BINDIR CMAKE_ARG |

## 交付物
| 文件 | 说明 |
|------|------|
| bin/bear | 主程序 (13MB) |
| lib/bear/wrapper | wrapper 程序 |
| lib/bear/libexec.so | intercept 共享库 |
| lib/bear/wrapper.d/* | wrapper 符号链接 |
| share/man/man1/* | man 页 |
---

**编译结束**: 2026-08-05 17:08
**最终状态**: built
