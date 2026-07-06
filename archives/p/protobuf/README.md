# protobuf

Google 的数据序列化格式库和编译器（protoc），用于跨语言跨平台的结构化数据交换。

## OHOS 适配

- **构建系统**: CMake（所有版本）
- **E092**: CMake 不识别 HarmonyOS 平台，通过 `CMAKE_SYSTEM_NAME=Linux` 绕过
- **ELF 签名限制**: Conan cache 中的 protoc 未签名无法直接执行，test_package 需预生成 proto 代码
- **静态编译**: `BUILD_SHARED_LIBS=OFF` 避免动态库 RPATH 问题
- **测试执行**: 测试二进制需通过 `bash -c` 包装执行，绕过 `/system/bin/sh` 对未签名 ELF 的限制

## 依赖

- v21.12: `zlib/1.3.1@ohpcd/stable`
- v34.1: `abseil-cpp`（通过 absl_DIR cmake 变量查找）

## 功能验证

- `protoc --version` → `libprotoc 3.21.12`（v21.12）
- Conan test_package: 5 个功能测试（序列化/反序列化往返、repeated 字段、ByteSize、默认值、字段清空）

## 参考

- 上游仓库: https://github.com/protocolbuffers/protobuf
- v21.12 发布: https://github.com/protocolbuffers/protobuf/releases/tag/v21.12
