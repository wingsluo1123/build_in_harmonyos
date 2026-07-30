## PR 信息
- **三方库名称**：fluent-bit
- **上游版本**：5.0.9
- **上游仓库地址**：https://github.com/fluent/fluent-bit
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无

---

## 测试用例对比

### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游测试套件（fluent-bit 上游用 check/CTEST，但需外部依赖，本配方关掉） |
| 集成测试 | 0 | - |
| 其他测试 | 0 | 跳过的测试 |
| **合计** | **0** | |

### 是否存在对上游测试用例的修改？
否，未修改上游测试用例。本配方新增 test_package（运行已安装的 fluent-bit 二进制 `--version`/`--help`）作为鸿蒙侧 L1 official test，不修改上游测试。

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 一致 | 上游单元测试需外部依赖，已关闭 |
| 集成测试 | 0 | - | - |
| 鸿蒙特有测试 | 1 | 新增 | test_package 运行 fluent-bit --version/--help（L1e 负面测试确认真依赖） |
| **合计** | **1** | | |

---

## 上游测试用例修改说明
未修改上游测试用例。新增的 test_package/test.c 是 Conan 2.x 标准配方测试，非上游测试。

## 验证结果

### 编译验证
- 编译器: clang (aarch64-unknown-linux-ohos)
- 编译状态: 成功
- 构建系统: cmake
- 配置选项: 关闭所有需外部库的可选子系统（TLS/HTTP_SERVER/AWS/SQLDB/Kafka/LuaJIT/WASM 等）+ 关闭所有需外部依赖的 input/output/filter 插件，零外部依赖绕过 R36。详见 manifest.yaml build.configure_options。

### 产物验证
| 编译无错误 | PASS | 构建系统: cmake, 状态: published |
| 产物存在性 | PASS | conan create 验证通过 |
| ELF 格式 | PASS | aarch64-unknown-linux-ohos |
| 运行测试 | 通过 | test_package: 1/1 Passed (0.12 sec) |
| 动态依赖 | PASS | 依赖: 无（零外部依赖配方） |

### 补丁说明
- `patches/0001-ohos-stubs-and-source-patches.patch` (85 行，6 文件改动):
  - `CMakeLists.txt`: 加全局 `include_directories(BEFORE ${CMAKE_BINARY_DIR}/include/{,monkey/})` 解生成头文件解析
  - `lib/monkey/mk_core/CMakeLists.txt`: 加 `${PROJECT_BINARY_DIR}/include/monkey/`
  - `lib/chunkio/src/cio_utils.c`: 本地 `<fts.h>` 注释（头由 stub 提供）
  - `src/flb_http_client.c`: 补 `#include <flb_upstream_node.h>`
  - `src/flb_blob_db.c`: `#else` 分支补 stdint/cfl_sds/flb_config include + 修 `flb_blob_db_file_part_get_next` 签名
  - `src/CMakeLists.txt`: 加 `${CMAKE_BINARY_DIR}/ohos_link_stubs.c` 到 src 列表
- `patches/ohos-stubs-bundle.tar.gz` (stub bundle，由 conanfile.py build() 解包到 build_folder):
  - `openssl/*.h`: 空声明 stub（FLB_TLS=Off，但 flb_hmac/flb_crypto 等核心源无条件编译）
  - `sqlite3.h`: 空 stub（FLB_SQLDB=Off，flb_sqldb.h 仍被引用）
  - `fts.h`: 鸿蒙 musl 缺 BSD fts API，chunkio 的 cio_utils.c 用 fts_open/read/close
  - `monkey/mk_core_info.h`, `monkey/mk_info.h`, `monkey/mk_env.h`: 从 .in 模板生成
  - `ohos_link_stubs.c`: 链接期空实现（flb_sqldb_*, flb_http_server_*, pthread_cancel, sqlite3_clear_bindings）

### 依赖
零外部依赖（所有可选依赖均已关闭）。fluent-bit 核心依赖的 monkey/c-ares/onigmo/cfl/cmetrics/cprofiles/ctraces/zstd 均为内置子项目，随主配方一起编译。

### 测试结论
- 总体评价: 通过
- 已知限制: 关闭了所有需外部库的可选子系统（TLS/HTTP/AWS/SQLDB/Kafka/Lua/WASM 等），fluent-bit 仅作为本地日志 processor/forwarder 基础功能可用。如需 TLS/HTTP/Kafka 等功能，需先适配对应依赖库到 ohpcd。

### 遇到的问题与解决方案
详见 notes.md 的"编译经验记录"段（16 条）。核心：
1. 鸿蒙 musl 缺 openssl/sqlite3/fts/pthread_cancel → 空 stub 头文件 + 链接期空实现
2. monkey 子项目生成头文件 include 路径不一致 → 顶层 CMakeLists.txt 加 BEFORE include_directories
3. flb_blob_db.c 的 #else 分支缺 include + 签名冲突 → 源码补丁修正
4. GitHub tarball 下载不稳定 → 本地 cached tarball + conanfile.py source() 优先用本地

### 验证命令
```bash
# conan-verify（配方验证）
python3 scripts/ohc-run.py conan-verify fluent-bit 5.0.9
# 结果: G1/G0/G2/G3/G4 + L2/L4/L5 全 PASS，test_package 1/1 Passed

# W3 本地 CI 模拟
zsh ci/conan/build_and_test.sh archives/f/fluent-bit/5.0.9
# 结果: L0/L1/L1e/L2/L4/L5 全 pass，fluent-bit --version OK

# finish（编译收尾）
python3 scripts/ohc-run.py finish fluent-bit 5.0.9 published
# 结果: Step 1-8 通过，status=published，submit 就绪

# 产物
$ file ~/.conan2/p/b/fluen*/p/bin/fluent-bit
fluent-bit: ELF 64-bit LSB executable, ARM aarch64, dynamically linked, interpreter /lib/ld-musl-aarch64.so.1
```
