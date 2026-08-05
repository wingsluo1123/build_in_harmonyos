# aws-c-auth 0.10.1 适配笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-08-05
- 编译器: Clang 15.0.4
- 状态: success

## 编译步骤
1. 下载源码 aws-c-auth-0.10.1.tar.gz
2. CMake 配置: `-DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTING=OFF`
3. 使用 CMAKE_PREFIX_PATH 指向依赖包目录（AWS CMake 模块兼容性）
4. `cmake --build` 编译成功，生成静态库
5. conan create 验证通过

## 依赖版本
- aws-c-common/0.14.3
- aws-c-cal/0.9.15 (含 aws-lc/5.4.0 加密后端)
- aws-c-sdkutils/0.2.7
- aws-c-io/0.27.5 (含 BYO_CRYPTO 平台适配补丁)
- aws-c-http/0.11.0
- aws-c-compression/0.3.2
- aws-lc/5.4.0

## 构建系统适配
- 使用 CMAKE_PREFIX_PATH 而非 CMakeDeps，因为 AWS C 库的 CMake 配置创建 AWS:: 命名空间目标
  并添加 CMake 模块（AwsCFlags, AwsCheckHeaders 等）到 CMAKE_MODULE_PATH
- CMakeDeps 会用 aws-c-common::aws-c-common 替换 AWS::aws-c-common，导致构建失败

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 依赖包未发布到制品仓 | 依赖 PR 尚未合并 | 将依赖配方包含在分支中，CI 使用 --build=missing 从源码编译 |
| 2 | CMakeDeps 与 AWS CMake 模块不兼容 | AWS 使用自定义 CMake 配置 | 使用 CMAKE_PREFIX_PATH 指向依赖包目录 |

## 验证结果
- 产物为纯静态库，无可执行二进制
- conan create 验证通过

## 注意事项
- 无可执行二进制，safety check 跳过
- 测试已禁用（BUILD_TESTING=OFF）
- test_package 验证 aws_auth_library_init 返回值检查
