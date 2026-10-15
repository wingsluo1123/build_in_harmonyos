# libkysdk-vector-engine-client 1.2.0.0 — HarmonyOS PC 适配笔记

## 概要

| 项 | 值 |
|----|----|
| 上游 | https://gitee.com/openkylin/libkysdk-vector-engine-client（openKylin，改自 milvus-sdk-cpp） |
| tag | `upstream/1.2.0.0`（orig 归档随 `debian/1.2.0.0-1` release 发布，内容一致） |
| 源码 sha256 | `fc5d7d1866496e0a4ab9307ce8c9c9c82dede1f37d79edb190a128fb9c42e2c6`（44310 B，strip_root） |
| 构建系统 | CMake（≥3.5），C++17，单 SHARED 库（VERSION 0.0.1 / SOVERSION 1） |
| 目标 | OHOS / armv8 / clang 15 / libc++ / Release（构建机即 aarch64 OHOS PC，protoc/grpc_cpp_plugin 原生可执行） |
| 依赖 | grpc/1.84.0（静态，传递 protobuf/33.6、abseil-cpp/20260107.1、c-ares、re2、openssl/3.5.6、zlib/1.3.1）、protobuf/33.6、libkylin-ai-system-private/1.2.0.0、nlohmann_json/3.12.0、zlib/1.3.1 |
| 补丁 | 0001（cmake config targets + zlib）单补丁 |
| 参照 | kylin-ai-document-service/1.2.0.0（同型 gRPC 宏消费者，先例配方）、grpc/1.84.0、libkylin-ai-system-private/1.2.0.0 |

## 1. 库语义与构建流

- 库本体 `src/`（Database 工厂 + MilvusClientImpl/MilvusConnection + types）；
  protobuf/gRPC 桩代码在**构建期**生成：CMakeLists 调用
  `kylin_ai_generate_grpc_proto_source(vector-db schema common msg feder rg milvus)`
  与 `kylin_ai_generate_grpc_proto_service(vector-db milvus)`——宏来自
  `find_package(KylinAiProto)`（libkylin-ai-system-private 包内
  share/KylinAiProto/cmake/KylinAiProtoGenerate.cmake）。
- `.proto` 源在 libkylin-ai-system-private 包内
  `share/kylin-ai/protocols/grpc/vector-db/*.proto`（9 个，本库用 6 个 .proto + milvus 服务桩；
  扁平 import，`-I ${SRC_DIR}` 一次解析全部）。
- 生成器：registry `protoc`（protobuf/33.6）+ `grpc_cpp_plugin`（grpc/1.84.0），
  均为 aarch64 musl ELF，构建机原生执行；grpc_cpp_plugin NEEDED libc++_shared.so →
  运行时 LD_LIBRARY_PATH 由 profile [buildenv] 指向 SDK llvm/lib。
- 产物闭包：静态 libgrpc++/libgrpc/libgpr/libprotobuf/absl/zlib 全部吸收进
  libkysdk-vector-engine-client.so，公共头无 gRPC/protobuf 依赖 → 下游消费者
  只需本包头 + 库本体。

## 2. 适配点与依据（原文/行号）

| 适配点 | 依据 |
|--------|------|
| `pkg_check_modules(GRPC REQUIRED IMPORTED_TARGET grpc)` → `find_package(gRPC CONFIG REQUIRED)`；产物 `PkgConfig::GRPC` 全树零引用，纯存在性检查；registry grpc.pc `Requires:` 大量未安装 absl_* 模块 | `archives/k/kylin-ai-document-service/1.2.0.0/patches/0001-CMakeLists.txt.patch`（同型替换）+ conanfile.py docstring |
| 裸名 `grpc++`/`protobuf` → `gRPC::grpc++`/`protobuf::libprotobuf` | 同上；`knowledge/drafts/DRAFT-grpc-component-rich-integration.md` |
| 显式 `find_package(zlib CONFIG REQUIRED)` + `zlib::zlib` | grpc/1.84.0 test_package/CMakeLists.txt 注释原文："libgrpc.a references zlib symbols (message_compress) but grpc's installed config does not propagate zlib" |
| zlib 非 PIC 静态归档进 DSO → `-Wl,--exclude-libs,ALL` | `archives/k/kylin-ai-document-service/1.2.0.0/conanfile.py` requirements()/generate() 注释（R_AARCH64_ADR_PREL_PG_HI21 实证） |
| 宏变量：`PROTOBUF_PROTOC_EXECUTABLE`（全大写）+ `Protobuf_PROTOC_EXECUTABLE`（驼峰）双注入；`GRPC_CPP_PLUGIN` 预置 cache 变量使宏内 `find_program` 直接命中 | registry protobuf/33.6 包 `lib/cmake/protobuf/protobuf-module.cmake:59-71`（UPPER→Camel 单向映射，全大写永不导出）；`KylinAiProtoGenerate.cmake` 第 7 行与两处 add_custom_command 读全大写；find_program 语义：cache 变量已定义则直接返回 |
| `KYLAI_GRPC_PROTOCOL_DIR` 指向 kylin 包协议目录 | `knowledge/drafts/DRAFT-8959-libkylin-ai-system-private-gdbus-grpc-hardcoded-paths.md`；libkylin 包补丁 0003 变量化 |
| `CMAKE_INSTALL_LIBDIR=lib`（配方变量，不动源码） | 上游 install() 三处 `${CMAKE_INSTALL_LIBDIR}` 未定义 → `.pc` 落绝对 `/pkgconfig`（设备越权写） |
| `CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG=-Wl,-soname,` | CMake 无 Platform/HarmonyOS.cmake → 无 soname；CI L5a 强制 DT_SONAME（build_and_test.sh:1542-1595） |
| protobuf 精确 33.6（勿升 33.6.1/34.1） | `knowledge/drafts/DRAFT-kylin-ai-document-service-protobuf33-json-print-options-rename.md`："尝试 33.6.1 会得到 Version conflict ... originates from grpc/1.84.0" |
| nlohmann_json/3.12.0（下划线名，勿混横线名 3.11.2） | `archives/n/nlohmann_json/`（3.1.1/3.12.0）与 `archives/n/nlohmann-json/`（3.11.2）为不同包 |
| ENABLE_DEMO 保持 OFF | demo/client/milvus.cpp:18 `#include <uuid/uuid.h>`，拖入本闭包外的 libuuid |

## 3. 测试：诚实申报

### 3.1 上游测试（不存在，如实申报 NO_UPSTREAM_TESTS）

实测 `upstream/1.2.0.0` 归档（52 文件全列表）：无 test/ 目录、无任何
enable_testing/add_test/CTest/BUILD_TESTING、无 Makefile test 目标；
demo/ 为手工示例（默认 OFF），非自动化测试。证据归档：
`runs/libkysdk-vector-engine-client-1.2.0.0/scout-evidence/verify/vec.orig.tar.gz`
（sha256 同上）与 progress.json `upstream_test.discovery`。

### 3.2 test_package（消费者视角 + OHOS 适配点断言）

| # | 断言 | 性质 |
|---|------|------|
| 1 | `Database::Create()` 返回实例 | DSO 加载 + 全静态闭包符号解析 |
| 2 | `Connect(127.0.0.1:1)` 返回非 OK Status | 真实 gRPC channel 建立（InsecureChannelCredentials→CreateCustomChannel→WaitForConnected），死端口优雅错误路径；timeout 500ms×重试上界 ~8s，无挂死 |
| 3 | 错误消息非空 | 非 canned value |
| 4 | `Disconnect()` 返回 OK | 干净回收 |
| 5 | 包负载：include/lib/pkgconfig/licenses 全在 prefix 内 | CMAKE_INSTALL_LIBDIR 注入生效（.pc 不落 /pkgconfig） |
| 6 | readelf：DT_SONAME == `libkysdk-vector-engine-client.so.1`（相对名） | OHOS 工具链适配生效（L5a 同源断言） |
| 7 | `--dyn-syms` 中 milvus 桩符号计数 > 0 | 设备上 protoc/grpc_cpp_plugin 代码生成真实发生并编入交付 DSO |

ctest `add_test` + build 阶段 `cmake.test()`（构建 uid 真实执行），
test() 阶段 can_run 再跑一次 + python 侧 payload/ELF 断言。

## 4. 权威 CI 实测记录

| 轮次 | 结果 | 要点 |
|------|------|------|
| R1 | conan create 失败（test_package ctest 1/1 Failed） | 主库编译链接全过（stub 分支），运行期暴露：`Database::Create()` 返回 SwClientImpl——上游按 `CMAKE_SYSTEM_PROCESSOR MATCHES "x86_64\|aarch64"` 门控，实测走了 sw_64 桩分支（全部方法返回 NOT_SUPPORTED）。修复：generate() 用 `tools.cmake.cmaketoolchain:user_toolchain` 前置注入；test_package 增补桩分支回归断言（Connect 不得返回 NOT_SUPPORTED）。 |
| R2 | conan create 失败（同 R1 现象） | 本机 conan 2.29.1 的 CMakeToolchain 对 OHOS 渲染**空 generic_system 块**（无 CMAKE_SYSTEM_NAME/CMAKE_SYSTEM_PROCESSOR），CMakeDetermineSystem 走宿主分支：本机 `uname -p` 返回 unknown（命令成功）、`uname -m` 正常=aarch64 → `CMAKE_SYSTEM_PROCESSOR` 被置为 "unknown" 并覆写工具链值。仅注入 processor 仍被覆写（R2 日志复现 `-- Building for unknown architecture`）。修复（on-device 用 CI 同款 conan_toolchain.cmake 探针实测验证）：snippet 同时注入 `CMAKE_SYSTEM_NAME=HarmonyOS`（切入交叉分支，尊重工具链值）+ `CMAKE_SYSTEM_PROCESSOR=aarch64`，project() 实见 `PROC=[aarch64]`。 |

## 5. 风险与备注

- 桩代码生成发生在设备构建机（aarch64 原生），无宿主工具缺口（grpc 1.84.0
  笔记 §3 的宿主工具问题在本库不存在——本库必须生成，而 protoc/plugin 都是
  目标机原生二进制）。
- `find_package(Protobuf REQUIRED)` 未加 CONFIG（保持上游原样）：
  registry protobuf 为 cmake_find_mode=none，双拼写 protoc 变量注入使
  宏在 module/config 任一解析路径下都可命中。kylin-ai-document-service
  同写法已在本 CI 全绿。
- 抽样链接闭包：lld 对 DSO 内未解析符号默认报错；0001 补丁 + 显式 zlib
  已覆盖 grpc++/protobuf/absl/zlib 闭包（kylin-ai-document-service 同闭包
  已验证）。
