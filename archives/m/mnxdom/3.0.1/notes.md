# mnxdom 3.0.1 适配笔记

## 官方来源核验（R39 官方源）
- 官方仓库：https://github.com/mnx-works/mnxdom （同名镜像 rpatters1/mnxdom，Arch/Fedora 打包同源）
- 标签：`v3.0.1`（GitHub tags API 返回 commit `488aa8757ec602c20ff8cf599a2c6857339d8e93`）
- tarball：https://github.com/mnx-works/mnxdom/archive/refs/tags/v3.0.1.tar.gz
- SHA-256：`1fc1799c76651a58f8bd88b69b098f263ebb9646604a544745b231373508ccb8`（实测下载后 sha256sum）
- 许可证：MIT
- 语言预检（R47）：`detected_language=cpp`；构建系统 `cmake`（`project(mnxdom LANGUAGES CXX VERSION 2.1)`）；
  源码统计 `.cpp/.h/.hpp` 占 100%（19 个 C++ 源文件）。**通过**。

## 编译环境
- 构建系统: cmake（上游 CMakeLists，cmake_minimum_required 3.14）
- 编译日期: 2026-10-13
- 编译器: clang / clang++ 15.0.4，libc++
- Conan: 2.29.1（OHOS 适配版），profile `ohos-aarch64`
  （os=OHOS 6.0 / arch=armv8 / clang 15 / libc++ / cppstd=17）
- 平台: 鸿蒙 PC（HarmonyOS/aarch64），原生构建（build = host = target）
- 链接形态: 静态（`shared=False`），产出 `libmnxdom.a`

## 项目结构
- CMake 库项目，库目标 `mnxdom`
- 公共头：`src/*.h`（含 `src/validation/Validation.h`、`src/util/*.h`），安装到 `include/mnxdom/`
- 源码：`src/EnumerationMaps.cpp`、`src/Implementations.cpp`、
  `src/validation/SchemaValidate.cpp`、`src/validation/SemanticValidate.cpp`
- 测试：`tests/`（GoogleTest，14 个 .cpp，共 62 个用例；`gtest_discover_tests` 注册到 ctest）
- 第三方数据：`third_party/w3c-mnx/`（随 tag 一起 vendored，含 `mnx-schema.json` 与官方示例 JSON）
- 另装 `lib/pkgconfig/mnxdom.pc`
- `docs/doxygen-awesome-css` 是唯一 submodule，仅文档用，构建不需要

## 编译步骤
```
python3 $SKILL_ROOT/scripts/ohc-run.py init-build mnxdom 3.0.1 \
  --url=https://github.com/mnx-works/mnxdom/archive/refs/tags/v3.0.1.tar.gz
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify mnxdom 3.0.1
# 等价于：
conan create archives/m/mnxdom/3.0.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```
配方内 CMake 关键变量：
`-DUSE_SYSTEM_NLOHMANN_JSON=ON -DUSE_SYSTEM_GOOGLETEST=ON
-DUSE_SYSTEM_JSON_SCHEMA_VALIDATOR=OFF
-DFETCHCONTENT_SOURCE_DIR_JSON_SCHEMA_VALIDATOR=<local src>
-DJSON_VALIDATOR_INSTALL=ON -DJSON_VALIDATOR_SHARED_LIBS=OFF
-Dnlohmann_json_schema_validator_SHARED_LIBS=OFF
-DGTest_DIR=<gtest 包内 lib/cmake/GTest> -Dmnxdom_BUILD_TESTING=ON`

## 依赖版本
| 依赖 | 版本 | 来源 | 说明 |
|------|------|------|------|
| nlohmann_json | 3.12.0 | ohpcd 制品仓 | header-only，与上游 `NLOHMANN_JSON_VERSION` 完全一致 |
| gtest | 1.17.0 | ohpcd 制品仓 | 仅测试期依赖（`test_requires`） |
| json-schema-validator | commit `40af3ec3` | 官方源码随配方下发（`conandata.yml` 的 `embedded_sources`） | 静态编译进本包一起交付，见问题 2 |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 CMakeLists 用 FetchContent 从 github 下载三个依赖 | 首次配置即联网拉源码，CI/离线环境不可控 | 打开上游自带的 `USE_SYSTEM_NLOHMANN_JSON` / `USE_SYSTEM_GOOGLETEST` 开关改用制品仓包；json-schema-validator 用 `FETCHCONTENT_SOURCE_DIR_*` 指向随配方下发的本地源码 |
| 2 | 用制品仓 `json-schema-validator/2.1.0` 时，上游测试 62 个用例**全部**失败 | MNX schema 是「根带 `$id`、子 schema 继承该 `$id`」的结构；2.1.0 在这种结构下会抛 `schema with <id> # <pointer> already inserted`。上游 mnxdom 正是为此把该依赖钉在 commit `40af3ec3` | 按上游钉住的 commit 从官方源取依赖源码（`conandata.yml` → `embedded_sources.json-schema-validator`，含 SHA256），用 `FETCHCONTENT_SOURCE_DIR_JSON_SCHEMA_VALIDATOR` 交给上游 FetchContent 就地编译。制品仓只有 2.1.0，而适配/发布依赖库属于另一个 PR（W2） |
| 3 | 内嵌依赖默认会被编译成共享库 | jsv 自身 CMakeLists 的静态/共享开关写错了变量名：option 是 `JSON_VALIDATOR_SHARED_LIBS`，实现里读的却是 `nlohmann_json_schema_validator_SHARED_LIBS` | 两个变量都显式置 `False`；并在 `package()` 里断言 `libnlohmann_json_schema_validator.a` 确实装进来了（装配错误直接报错，不留半成品） |
| 4 | mnxdom 链接 `GTest::gtest_main` / `GTest::gtest` 找不到目标 | CMakeDeps 只为 gtest 生成 `gtest::gtest`，且没有 `gtest_main` 目标 | `GTest_DIR` 指向 gtest 依赖包内自带的上游 CMake 配置（可重定位，导出全套 `GTest::` 目标；同仓库 abseil 配方同法）。上游固定 googletest 1.15.2，制品仓只有 1.17.0，但 `GTestConfigVersion.cmake` 是 `SameMajorVersion` 策略，1.15.2 的约束由 1.17.0 满足，无需补丁 |
| 5 | test_package 编译报 `'nlohmann/json.hpp' file not found` | mnxdom 公共头 `#include "nlohmann/json.hpp"`；CMakeDeps 不会为「无组件」的依赖自动生成 `find_dependency`（生成的 `mnxdom_FIND_DEPENDENCY_NAMES` 为空） | test_package 显式 `requires("nlohmann_json/3.12.0")` + `find_package(nlohmann_json)`（与同仓库 json-schema-validator 的 test_package 同一处理方式） |
| 6 | C++ 标准 | 上游默认 `CMAKE_CXX_STANDARD 23`，只要求 ≥17 | Conan Toolchain 按 profile 传 `CMAKE_CXX_STANDARD=17`，上游逻辑遵从该值（≥17 校验通过），按 C++17 构建，测试全绿 |

## 源码修改

无。本版本不产生 patches（`patches: {}`）——上述问题全部通过 Conan 配方接线与上游自带开关解决，
未改动上游任何源文件（符合 R2/R8）。

## 验证结果

```
$ python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify mnxdom 3.0.1
✅ G0 PASS（预构建风险评估）
✅ G1 PASS（配方完整性）
✅ G2 PASS（conan create 干净构建）
✅ G3 PASS（系统同名库隔离验证 R26）
⚠️ G4 工具未取到程序包 ID（未见失败）
✅ 配方验证通过: mnxdom 3.0.1
```

上游官方测试（`conanfile.py` 的 `build()` 内 `cmake.test()` → ctest）：
```
100% tests passed, 0 tests failed out of 62
```
62 个用例 = `tests/*.cpp` 与 `tests/validation/*.cpp` 中的 62 个 `TEST()`（与 ctest 发现数一致）。

test_package（消费者视角，真实调用 API）：
```
mnxdom test_package: 15/15 checks passed
```

消费者用例（端到端业务流程，`test_consumer/consumer_use_case.sh`，鸿蒙特有）：
```
PASS: C0 消费者程序编译+链接 (libmnxdom.a + 随包交付的 json-schema-validator)
PASS: C1 业务全流程执行 (载入→校验→编辑→导出→回读复核, rc=0)
PASS: C2 业务报告与期望一致 (measures=3 parts=1 layout=layout0 fraction=3/8)
PASS: C3 输出 consumer-ok 成功标记
PASS: C4a 导出 MNX 工程文件非空 (1206 字节)
PASS: C4b 导出工程含业务补齐的 measure/part/layout/score 结构
--- 消费者用例: ALL PASS ---
```
用例复现：
```
conan install --requires=mnxdom/3.0.1@ohpcd/stable -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --deployer=full_deploy --output-folder=$TMPDIR/deploy-mnxdom
sh archives/m/mnxdom/3.0.1/test_consumer/consumer_use_case.sh \
  "$TMPDIR/deploy-mnxdom/full_deploy/host/mnxdom/3.0.1/Release/armv8" <nlohmann_json 前缀>
```

## 注意事项
- MNX JSON schema 通过 `src/validation/SchemaValidate.cpp` 里的 `#include "mnx-schema.xxd"`
  以十六进制数组内嵌到库中，`validation::schemaValidate()` 运行时**不读外部 schema 文件**；
  因此安装包无需附带 `third_party/w3c-mnx` 资源，消费端也不需要 `MNX_W3C_SCHEMA_PATH`。
- `MNX_W3C_SCHEMA_PATH` / `MNX_W3C_EXAMPLES_PATH` 是 PUBLIC 编译宏，指向**构建期源码目录**，
  仅供上游测试运行期读取示例数据；它们不会经由 CMakeDeps 传给下游。
- 本库不是系统同名库（系统 `/lib`、`/lib64` 下无 `libmnxdom`），R26 不适用；
  配方按仓库惯例默认 `shared=False`（与上游 `BUILD_SHARED_LIBS` 默认 OFF 一致）。
- 消费端除 `mnxdom/3.0.1` 外还需显式 `requires("nlohmann_json/3.12.0")`（公共头依赖），
  详见 `README.md`。
- 上游 CMake 工程版本号仍是 `2.1`（`project(mnxdom ... VERSION 2.1)` 未随 tag 更新），
  生成的 `mnxdom.pc` 里 `Version:` 会显示 2.1；Conan 包版本以 tag `v3.0.1` 为准，即 `mnxdom/3.0.1`。
- `json-schema-validator` 自带的 CMake 导出文件会把安装期绝对路径写死（不可重定位），
  本包不经它导出，`package()` 中已删除该目录，消费端统一走 CMakeDeps。
---

**编译结束**: 2026-10-13 18:40
**最终状态**: built
