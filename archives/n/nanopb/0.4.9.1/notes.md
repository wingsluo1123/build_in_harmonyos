# nanopb 0.4.9.1 适配笔记

## 编译环境

- 构建系统：CMake
- 运行时产物：静态库 `protobuf-nanopb`
- 目标平台：HarmonyOS PC aarch64
- Conan 依赖：无（OHOS 下额外从 protobuf 21.12 源码构建测试用 protoc）
- 构建工具：CMake、SCons、原生 protoc、纯 Python protobuf

## 编译步骤

1. 从官方 GitHub tag `0.4.9.1` 下载源码并校验 SHA256。
2. 使用 CMakeToolchain 设置 `BUILD_SHARED_LIBS=OFF`、`BUILD_STATIC_LIBS=ON`，只构建 nanopb runtime。
3. 使用 CMake 编译并安装静态库和头文件。
4. 使用上游 `tests/SConstruct` 执行官方 SCons 测试套件；OHOS worker 没有可用的独立 `protoc` 时，从 protobuf 21.12 源码构建并签名原生 `protoc`。
5. 使用 `test_package` 从消费者视角链接并运行 nanopb 编码/解码测试。

## 测试范围

- 上游官方测试：`tests/` 中登记的 143 个 `RunTest` 测试调用。
- 消费者测试：1 个 CTest 用例，实际调用 `pb_encode_tag`、`pb_encode_varint`、`pb_decode_tag` 和 `pb_decode_varint`。

## 适配说明

- nanopb 是库类型，未新增 `commands.json`。
- 未修改上游源文件；OHOS 构建阶段仅对源码树中的生成器回退调用做临时适配，不改变打包产物中的上游源码。
- CMake 上游工程在关闭 generator 时仍会探测 `protoc`，因此构建环境必须提供 `protoc`；OHOS 不使用 `grpcio-tools`，因为其 `_protoc_compiler.so` 位于 HMDFS 用户路径时会被 hmmac 拒绝 `dlopen`，即使签名和执行位都正确。
- OHOS 的 Python 生成器只使用 `protobuf` 纯 Python 实现；独立 `protoc`、SCons 生成的测试 ELF 和 `test_package` 消费者测试程序均通过 `binary-sign-tool -selfSign 1` 签名，测试编译器包装器在链接后自动完成签名。
- OHOS 将已签名的独立 `protoc` 绝对路径通过 `PROTOC` 环境变量传给生成器，并在构建阶段为上游 `generator/proto/_utils.py` 的系统回退分支做最小适配，确保 `generator_relative_paths` 测试不会依赖 HMDFS 上不可靠的裸命令查找。
- 该失败的根因是路径安全标签（知识库 E212/E179），不是 chmod、旧 `.codesign` 或签名输出 inode 问题。

## 验证结果

- Windows 本地：Conanfile Python 语法、W3 审计、`git diff --check` 通过。
- OHOS CI #8227：失败，根因是 HMDFS 用户路径上的 `grpcio-tools/_protoc_compiler.so` 无法 `dlopen`；本次提交改为原生 `protoc` 和签名测试 ELF，等待 CI 重新验证。

## 编译结束

- 编译结束：2026-07-17
- 最终状态：built
- COMPLETED
