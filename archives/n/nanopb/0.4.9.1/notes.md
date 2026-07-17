# nanopb 0.4.9.1 适配笔记

## 编译环境

- 构建系统：CMake
- 运行时产物：静态库 `protobuf-nanopb`
- 目标平台：HarmonyOS PC aarch64
- Conan 依赖：无
- 构建工具：CMake、SCons、protoc、Python protobuf

## 编译步骤

1. 从官方 GitHub tag `0.4.9.1` 下载源码并校验 SHA256。
2. 使用 CMakeToolchain 设置 `BUILD_SHARED_LIBS=OFF`、`BUILD_STATIC_LIBS=ON`，只构建 nanopb runtime。
3. 使用 CMake 编译并安装静态库和头文件。
4. 使用上游 `tests/SConstruct` 执行官方 SCons 测试套件；为兼容上游 SCons 命令拼接，向 `PROTOCFLAGS` 提供尾随空格。
5. 使用 `test_package` 从消费者视角链接并运行 nanopb 编码/解码测试。

## 测试范围

- 上游官方测试：`tests/` 中登记的 143 个 `RunTest` 测试调用。
- 消费者测试：1 个 CTest 用例，实际调用 `pb_encode_tag`、`pb_encode_varint`、`pb_decode_tag` 和 `pb_decode_varint`。

## 适配说明

- nanopb 是库类型，未新增 `commands.json`。
- 未修改上游源文件，也未新增补丁。
- CMake 上游工程在关闭 generator 时仍会探测 `protoc`，因此构建环境必须提供 `protoc`；generator Python 模块不作为本 Conan 库产物安装。

## 验证结果

- `conan create .../0.4.9.1 --build=missing -pr:h=default -pr:b=default`：通过。
- 上游官方 SCons 测试：143/143 通过；测试在 Conan `build()` 阶段执行。
- `test_package`：1/1 CTest 通过。
- `ci/conan/build_and_test.sh`（Linux profile 的隔离 CI 模拟）：L0/L1/L4/L5 通过，L2 按库无命令行程序规则跳过。
- `ci/scripts/preflight_check.sh nanopb/0.4.9.1`：通过，无依赖需要检查。
- `git diff --check` 和 Conanfile Python 编译检查：通过。

## 编译结束

- 编译结束：2026-07-17
- 最终状态：built
- COMPLETED
