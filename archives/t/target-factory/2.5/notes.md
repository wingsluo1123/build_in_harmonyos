# target-factory 2.5 适配笔记

## 编译环境
- 构建系统: CMake (`project(target-factory VERSION 2.5.0)`)
- 编译日期: 2026-10-17
- 编译器: clang 15 (OHOS SDK), C++17, Release
- 依赖: unilog/2.5, protobuf/21.12
- 状态: built

## 编译步骤

```bash
conan create archives/t/target-factory/2.5 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  -r=ohpcd --build=missing
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `protobuf_generate_cpp` 未定义 | OHOS protobuf 包设置 `cmake_find_mode=none` 并使用上游 config，只有 module 兼容模式才提供该宏 | `protobuf_MODULE_COMPATIBLE=ON` |
| 2 | `protoc executable not found` | FindProtobuf 不搜索 Conan 包的 `bin/` | `Protobuf_PROTOC_EXECUTABLE=<protobuf>/bin/protoc` |
| 3 | `PROJECT_GIT_COMMIT_ID` 未定义 | Debian orig tar 无 `.git`，`#cmakedefine` 留空 | patch 0002 改为无条件 `#define`（空值） |
| 4 | clang 15 `-Werror` 失败 | 上游 `VitisCommon.cmake` 强制 `-Werror -std=gnu++14` | patch 0001 移除 `-Werror` 和硬编码标准 |
| 5 | 测试二进制 rc=127 | 构建树无安装 rpath，加载不到 `libunilog.so` 的依赖 | 执行测试时注入 `LD_LIBRARY_PATH`（构建树 + 依赖包 lib） |
| 6 | 消费者 `find_dependency(protobuf)` 失败 | OHOS protobuf 包 `cmake_find_mode=none`，CMakeDeps 不生成 config；若把 protobuf 写进 `cpp_info.requires`，生成的 `find_dependency(protobuf)` 永远找不到 | protobuf 改为 `visible=False` 私有依赖，不进入消费者的 `cpp_info.requires`；需要 `target.pb.h` 的消费者自行注入 `protobuf_DIR`（test_package 演示） |
| 7 | 安装库缺少 DT_SONAME（CI L5a/L5c） | OHOS 未映射到 CMake 的 Linux 平台模块，`CMAKE_SHARED_LIBRARY_SONAME_<LANG>_FLAG` 为空，`VERSION/SOVERSION` 被忽略、`install(EXPORT)` 写出 `IMPORTED_NO_SONAME` | 配方注入 `-DCMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG=-Wl,-soname,` + `-DCMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE`；`readelf -d` 确认 SONAME=libtarget-factory.so |
| 8 | `DT_NEEDED` 记录 Conan 缓存绝对路径（CI L5b，导致 CI 侧 test_package 失败） | 已发布的 `unilog`/`glog`/`gflags` 自身没有 DT_SONAME，CMake 链接其导入目标时按绝对路径传入 | patch 0003 改为 `target_link_directories()` + 按名链接（配方注入 `TARGET_FACTORY_SONAME_LIBS`/`TARGET_FACTORY_SONAME_LIBDIRS`），`unilog::unilog` 仅保留 include/宏接口；不要用 patchelf 事后改写（musl 加载失败） |

| 9 | CI 摘要显示 `Conan test_package: 失败`，但构建步骤与 L1 门禁全绿 | 摘要按仓内统一 schema 解析 `HMBS_TEST_PACKAGE_RESULT`，本包原先输出 `{"status":"passed",...}`，缺 `executed`/布尔 `passed`/`passedCount`，被判失败 | 用例与 `test_package/conanfile.py` 均改输出 `{"executed":true,"passed":<bool>,"command":...,"discovered":12,"passedCount":12}` |

## 上游测试

`test/CMakeLists.txt` 生成 3 个可执行文件但没有 `add_test`，因此不跑 ctest，
由 `build()` 直接执行：

| 测试 | 命令 | 说明 |
|------|------|------|
| test_factory | `test_factory DPUCAHX8H_ISA2` | 按名称创建 target 并 dump |
| test_fingerprint | `test_fingerprint <fingerprint>` | 用 test_factory 输出的指纹反向创建 target |
| test_lib_info | `test_lib_info` | 库名 / lib id |

## 验证结果

- `conan create archives/t/target-factory/2.5 ... --user=ohpcd --channel=stable`：退出码 0
- 上游测试：3/3 通过（`test_factory DPUCAHX8H_ISA2`、`test_fingerprint <hex>`、`test_lib_info`）
- 鸿蒙消费者测试：1/1 通过，12 项断言（注册检查、按名创建、type/ISA 校验、指纹双向往返、dump 文件、`get_lib_name`）
- `readelf -d libtarget-factory.so`：SONAME = `libtarget-factory.so`

```
HMBS_UPSTREAM_TEST_RESULT={"status": "passed", "framework": "executables",
  "discovered": 3, "executed": 3, "passed": 3, "failed": 0, "skipped": 0}
HMBS_TEST_PACKAGE_RESULT={"executed": true, "passed": true,
  "command": "./test_target_factory", "discovered": 12, "passedCount": 12}
```

`HMBS_TEST_PACKAGE_RESULT` 采用仓内统一 schema（`executed`/`passed` 为布尔，配
`discovered`/`passedCount` 计数）：CI 摘要按该 schema 解析，写成
`{"status":"passed"}` 时平台会把 test_package 判成失败（本轮实测）。消费者用例与
`test_package/conanfile.py` 各输出一次，两处计数一致。

## 已知限制

- `unilog` 包的 `DT_NEEDED` 仍写有它构建期的 glog/gflags 绝对路径（上游包缺陷，
  不在本包可控范围）；运行时需保证 `libglog.so`/`libgflags.so` 在库搜索路径中
  （Conan 虚拟运行环境已注入），否则加载 `libunilog.so` 时报
  `Error loading shared library`。
- 消费者若编译包含 `target.pb.h` 的代码，需要自行指向 protobuf 的 CMake config
  （`protobuf_DIR=<pkg>/lib/cmake/protobuf`），并链接 `protobuf::libprotobuf`。

## 交付物

| 文件 | 说明 |
|------|------|
| libtarget-factory.so（SONAME=libtarget-factory.so） | 共享库 |
| include/vitis/ai/target_factory.hpp, target.pb.h | 头文件 |
| share/cmake/target-factory/* | CMake config / export |

## 注意事项
- target 描述在构建期编码进库，运行时无需 `targets/` 目录
- `dump()` 写入当前工作目录，调用方需保证可写

## 知识沉淀

- 问题表第 8 条（依赖包无 `DT_SONAME` → 产物 `DT_NEEDED` 烙印 Conan 缓存绝对路径）已
  提交知识草稿 `knowledge/drafts/DRAFT-ohos-cmakedeps-soname-less-dep-link-by-name.kv`
  及配套 `.md`；第 7 条与既有草稿
  `DRAFT-cmake-harmonyos-system-name-soname.kv` 同源，本次为其在 CMakeDeps 消费面的补充。

## 最终状态: built

上游测试 3/3、鸿蒙消费者测试 1/1 全部通过；`conan create` 退出码 0。
---

**编译结束**: 2026-10-17 20:01
**最终状态**: built
