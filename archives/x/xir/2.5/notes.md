# xir 2.5 适配笔记

## 编译环境
- 构建系统: cmake（上游硬编码 add_library(xir SHARED)，Ninja 生成器 E074）
- 编译日期: 2026-10-17
- 编译器: clang/clang++ 15（/data/service/hnp/bin，OHOS SDK aarch64 sysroot）
- 状态: published

## 编译步骤

1. W0 依赖前置：unilog/2.5、boost/1.85.0、protobuf/21.12、glog/0.7.1、
   gflags/2.2.2、zlib/1.3.1 全部 `conan download` 验证可消费（R36），全绿。
2. conan create（bare cmake 模式，先例 mgard/1.6.0）：
   - `_find_deps_preload()` 经 `CMAKE_PROJECT_TOP_LEVEL_INCLUDES` 在
     project() 前注入 FIND_ROOT_PATH/PREFIX_PATH/MODULE_PATH（放宽
     ohos.toolchain.cmake 的 FIND_ROOT_PATH_MODE_* ONLY 限制），
     `CMAKE_HAVE_LIBC_PTHREAD=ON`（ohos toolchain 下 -pthread
     try_compile 失败）、`Boost_INCLUDE_DIRS` 显式 set。
   - `-G Ninja -DCMAKE_TOOLCHAIN_FILE=<ohos.toolchain.cmake>
     -DCMAKE_CXX_FLAGS="-Wno-unused-command-line-argument"`（--gcc-toolchain
     unused + 上游 -Werror）。
   - BUILD_TEST=ON 构建上游 test/ 11 个 main 程序。
   - E077/ML-0043：构建树与包内 .so/可执行剥 `.codesign` 后
     `binary-sign-tool -selfSign 1` 重签。
3. 上游测试：签名后逐项执行 test/*.bin（LD_LIBRARY_PATH 指向构建树与
   依赖包 lib 目录）；fixture gen_xmodel.cpp 生成带 DPU 属性的
   fixture_dpu.xmodel 供 test_deserialize_model 使用。
4. test_package：CMakeDeps/CMakeToolchain 消费 xir::xir，编译运行
   新增鸿蒙消费者用例（建图→serialize→deserialize→校验往返一致）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | ohos toolchain 下 `Could NOT find Threads` | toolchain 下 -pthread try_compile 失败 | preload 注入 `CMAKE_HAVE_LIBC_PTHREAD=ON` |
| 2 | clang `unused argument --gcc-toolchain` | 上游 -Werror 全开 | CMAKE_C(XX)_FLAGS 加 -Wno-unused-command-line-argument |
| 3 | PROJECT_GIT_COMMIT_ID 等未定义 -Werror | 非 git 树构建 | config.hpp.in 改 `#define`（patch 0001） |
| 4 | vector<bool> 代理引用 -Werror（VVEC 宏） | libc++ vector<bool> 代理 `const auto&` | `for (const cpp_type v : x)` 显式元素类型 |
| 5 | test_deserialize_model 报 weights 2 维 | xir 内置 op 表要求 conv2d weights 4 维 NCHW | fixture/consumer 用 shape {1,1,8,8} + data {1,8,8,8} |
| 6 | 上游测试 REQUIRED attr aborts（bad_any_cast） | 测试代码与内置 op 表漂移 | patch 注入 xir_test_*_attrs() helpers（shape/data_type/pad_mode/axis） |
| 7 | test_subgraph_topo 需 graphviz dot | OHOS 设备无 graphviz | 显式 skip 并披露（2 skipped 之一） |
| 8 | libunilog.so 绝对 NEEDED 指旧家 ~/.cache/conan2 | 依赖包构建期缓存路径写死 | `_bridge_dep_needed_paths()` symlink 桥接 |
| 9 | test_package fatal: UniLog/UniLog.hpp not found | **CMakeDeps traits 剥离**：xir 为 shared-library，transform_downstream 对传递依赖 unilog/boost 向下游硬编码 headers=False/libs=False，CMakeDeps 据此清空 unilog_INCLUDE_DIRS_RELEASE；而 xir 公共头 attrs.hpp include UniLog.hpp | package_info 把 unilog/boost 的绝对 includedirs append 进 xir cpp_info（unilog recipe "EA header-only draft" 同款先例） |
| 10 | glog `<glog/logging.h> was not included correctly` | glog 0.7 要求消费方显式声明 GLOG_USE_GLOG_EXPORT | xir cpp_info.defines = ["GLOG_USE_GLOG_EXPORT"] 传播 |
| 11 | consumer test 运行期 XIR_INVALID_ARG_OCCUR | test.cpp conv2d weights 2 维 | 改为 4 维 {1,1,8,8}（与 fixture 同坑同解） |

## 源码修改

按文件拆分补丁 `patches/0001-0017-*.patch`（17 文件，refresh-patch --auto 从
orig→work 差异生成，与 tgt/lcrq 先例一致）：
- config.hpp.in：PROJECT_GIT_* `#cmakedefine` → `#define`
- serialize_v2.cpp：VEC 宏迭代 vector<bool> 代理修复
- shape_inference.cpp：去 lambda 捕获 out、is_simple_slice 加 (void)
- tensor_imp.hpp/cpp：to_string override、`\|` → `\|\|`
- hash-library 6 文件：swap `[[maybe_unused]]`
- tools/cmd_dump_code.cpp：create_parent_path `[[maybe_unused]]`
- 6 个测试文件：注入 xir_test_const_attrs()/data/concat helpers，
  `set_attr<int>("pad_mode", 0)` → `set_attr<std::string>("pad_mode", "SAME")`

配方级修改（无上游改动）：
- conanfile.py：bare cmake + preload、_bridge_dep_needed_paths、
  no-op graphviz dot shim（PATH 前置，test 中 save_to_dot 相关逻辑
  得以真实执行后再行渲染输出）、package_info traits 剥离修复 +
  GLOG_USE_GLOG_EXPORT 传播
- packaging/gen_xmodel.cpp：fixture（上游无样例 xmodel）

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| unilog | 2.5 | Xilinx 日志库（PUBLIC，cpp_info.requires） |
| boost | 1.85.0 | graph/property_tree（PRIVATE） |
| protobuf | 21.12 | xmodel 序列化（PRIVATE，Module 模式） |
| glog/gflags/zlib | 0.7.1/2.2.2/1.3.1 | unilog 传递依赖 |

## 验证结果

```bash
# conan create（round 28，一份日志完整证据链）
HMBS_UPSTREAM_TEST_RESULT={"status": "passed", "framework": "upstream test/ mains (no add_test registry)",
  "command": "cmake --build build-ohos; ./test/test_*.bin",
  "discovered": 11, "executed": 9, "passed": 9, "failed": 0, "skipped": 2}
# 上游测试明细（reports/upstream-test.log）：
#   pass  demo.bin / test_deserialize_model.bin / test_graph_impl.bin /
#         test_graph_iso.bin / test_graph_template.bin / test_md5sum.bin /
#         test_subgraph.bin / test_subgraph_iso.bin / test_subgraph_tensors_sort.bin
#   skip  test_deserialize.bin（上游硬编码开发者本机路径）
#         test_subgraph_topo.bin（需外部 graphviz dot）
# test_package（新增鸿蒙消费者用例）：
HMBS_TEST_PACKAGE_RESULT={"executed": true, "passed": true, "discovered": 1, "passedCount": 1}
# HMBS xir consumer test passed: serialize/deserialize round-trip OK
# conan-verify：G0/G1/G2/G3/G4 全 PASS，可标记 published
```

## 注意事项

- CMakeDeps traits 剥离是本包最大坑：shared-library 包的公共头若引
  传递依赖的头，消费者编译必然找不到头——必须在自身 cpp_info 显式
  append 依赖绝对 includedirs（unilog "EA header-only draft" 先例）。
- xir 公共头链 attrs.hpp → UniLog.hpp → glog/logging.h，消费者还需
  GLOG_USE_GLOG_EXPORT 宏（cpp_info.defines 传播）。
- 上游仅支持 SHARED（add_library 硬编码），shared=False 被 validate()
  拒绝。
- protobuf 用 21.12（OHOS armv8 二进制已发布）；3.17.3 无二进制，
  源码构建会挂 project() 编译器检查（libarcus notes 实证）。
---

**编译结束**: 2026-10-17 21:39
**最终状态**: published
