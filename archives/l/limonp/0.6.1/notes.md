# limonp 0.6.1 适配笔记

## 编译环境
- 构建系统: cmake（上游 cmake_minimum_required 2.6；配方 generate() 传 CMAKE_POLICY_VERSION_MINIMUM=3.5）
- 编译日期: 2026-10-04
- 编译器: clang/clang++（aarch64-linux-ohos，libc++）
- 状态: published（conan-verify G0-G4 全过，finish W2/W3 通过）

## 编译步骤

1. `ohc-run.py init-build limonp 0.6.1`（官方 tag v0.6.1 tarball）
2. `lang-preflight`：检测 cpp，匹配
3. 本地 cmake configure/build：`cmake -S . -B build -DCMAKE_POLICY_VERSION_MINIMUM=3.5` + `make -j1`
4. `ctest -V`：3/3 ctest、35/35 gtest 通过（详见 reports/test-report.md 双口径台账）
5. `conan-init` → 手写 header-only CMake 配方（v0.6.1 无 add_library(limonp)，头文件直接打包）
6. `conan-verify`：G0-G4 全过
7. `finish published`：W2 结构 + R36 依赖 + W3 本地 CI（conan create + ctest）全过，
   `.ci-result.json` 由工具写入（integrity_hash + log_sha256）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `'tr1/unordered_map' file not found`（G2/本地编译首错） | 老代码 `#elif(__cplusplus == 201103L)` 精确匹配 C++11；OHOS 固定 C++17，掉进 tr1 fallback，libc++ 无 tr1 | patch 0002：放宽为 `>= 201103L` |
| 2 | `no member named 'ptr_fun' / 'bind2nd'` | C++17 移除 std::ptr_fun/bind2nd/not1 | patch 0003：LTrim/RTrim 改 lambda |
| 3 | MutexLock.Test1 恒失败（res 为空，Release 必现、Debug 偶过） | `assert(!pthread_create(...))` 在 Release（NDEBUG）下整体被裁剪，线程从未创建 | patch 0005：先调用再断言 |
| 4 | FileLockTest.Test1 失败（Open 失败） | 测试硬编码 `/tmp/limonp_test_filelock`，OHOS /tmp 是只读 erofs | patch 0004：改用 getenv(TMPDIR) 回退当前目录 |
| 5 | ctest 只在 build 目录恰为源码根子目录时全过 | ADD_TEST 相对路径 COMMAND + fixture "../test/testdata/..." 依赖目录布局 | patch 0001：ADD_TEST 换 `$<TARGET_FILE:...>` + WORKING_DIRECTORY ${PROJECT_SOURCE_DIR}/test |
| 6 | CMake 4.x 拒绝 cmake_minimum_required(2.6) | CMake ≥4 移除 <3.5 兼容 | 配方 generate() 传 CMAKE_POLICY_VERSION_MINIMUM=3.5 |

## 源码修改（5 个补丁）

- 0001-CMakeLists.txt.patch：3 个 ADD_TEST → TARGET_FILE + WORKING_DIRECTORY
- 0002-include-limonp-StdExtension.hpp.patch：`== 201103L` → `>= 201103L`
- 0003-include-limonp-StringUtil.hpp.patch：ptr_fun/bind2nd → lambda
- 0004-test-unittest-TFileLock.cpp.patch：/tmp → $TMPDIR
- 0005-test-unittest-TMutexLock.cpp.patch：assert(副作用) → 先调用再断言

## 依赖版本

- 运行时：无（header-only）
- 测试：上游 vendored gtest（test/gtest，2016 版，本地编译；无 FetchContent 联网）
- 工具：clang 15 / CMake 4.1 / conan 2.29.1

## 验证结果

- ctest 3/3：`100% tests passed, 0 tests failed out of 3`
- gtest 35 执行/35 通过（源码声明 36，TCastFloat.cpp 引用不存在的 CastFloat.hpp 且上游未收录 → 未实例化 1）
- 消费者 test_package 5 组断言全过（含 GBK 0xD6D0 字节对打包 char 有符号性鸿蒙特有断言、std::thread 一致性）
- conan-verify：G0（预扫）/G1（配方完整）/G2（conan create 干净构建）/G3（系统同名库隔离）/G4（产物完整）全过

## 知识候选台账（knowledge_candidate_ledger）

任务类型：知识库扩展（path B 候选）。逐项四范围查重（graph 正式/E*.kv、doc/、drafts/、index.tsv）：

| 候选 | 真实错误/根因 | 修复 | 验证 | 可跨库复用 | graph/doc/drafts 查重 | 决定 |
|------|--------------|------|------|-----------|----------------------|------|
| 1. `__cplusplus == 201103L` 精确匹配 → tr1 fallback | v0.6.1 StdExtension.hpp 用精确相等分支，C++17 掉进 `<tr1/unordered_map>`，libc++ 无 tr1 | 放宽 `>= 201103L` | G2 复现 + conan create 修复后全绿 | 是（2000-2016 年代代码普遍） | 四范围未命中（E130/E218/E224/E293 同族不同触发；kytea 是 boost 路径） | **new_draft**（DRAFT-limonp-0.6.1-cpp11-exact-match-tr1-fallback.kv/.md 已建） |
| 2. std::bind2nd/ptr_fun C++17 移除 | StringUtil.hpp LTrim/RTrim 用 std::not1(bind2nd) | lambda | 同上 | 是 | drafts 已存在 DRAFT-coinor-vol-1.5.4-std-bind2nd-removed-cpp17（完全覆盖） | **reuse_existing**（similar_to 挂到新草稿） |
| 3. assert(pthread_create) NDEBUG 裁剪 | TMutexLock 放副作用于 assert 参数，Release 裁剪 | 先调用再断言 | Debug/Release 双跑 | 是 | graph 已存在 E259（hoist-side-effect-out-of-assert 完整覆盖） | **reuse_existing**（E259 命中） |
| 4. /tmp 只读（测试硬编码） | FileLock 测试写 /tmp，OHOS erofs | getenv(TMPDIR) | G2 全绿 | 是 | graph 已存在 E002（/tmp read-only set-env-var） | **reuse_existing**（E002 命中） |
| 5. ADD_TEST 相对路径 fixture | 依赖 build 目录布局 | TARGET_FILE + WORKING_DIRECTORY | 兄弟目录布局验证双过 | 是 | drafts 已存在 DRAFT-limonp-1.0.2…（同库 1.0.2 同问题已建）+ DRAFT-memtailor | **reuse_existing**（同 stem 家族已覆盖） |

### 七轴查重（对 DRAFT-limonp-1.0.2-… + coinor-vol + E259/E002）

- exact_duplicate：否（无新差异已覆盖的完整重复项；候选 2/3/4/5 均已命中既有条目）
- causal_duplicate：否（候选 1 触发面是新精确匹配陷阱，非既有条目根因）
- trigger_overlap：部分（候选 1 与 E218/E224/E293 同属"旧代码在新 C++ 标准下编译失败"族，但触发关键字/报错面不同）
- solution_overlap：部分（候选 1 与 coinor-vol 同在"头文件内改现代标准库用法"，但精确匹配改写是独立做法）
- combination_novelty：是（"精确相等 + tr1 fallback + libc++"组合无既有条目）
- boundary_novelty：是（限定 cppstd≥17 且 libc++ 无 tr1 的 OHOS 平台面）
- test_migration_novelty：是（无既有条目携带 tr1/unordered_map 断言）

### 关系字段
- similar_to：E218、E224、E293、DRAFT-coinor-vol-1.5.4-std-bind2nd-removed-cpp17、DRAFT-kytea-0.4.7
- caused_by：（无）
- prerequisite_of：（无）
- conflicts_with：（无）

### 路径决定
- **new_draft**：候选 1 已验证、可跨库复用、四范围查重未命中且存在新增差异 → 建
  DRAFT-limonp-0.6.1-cpp11-exact-match-tr1-fallback.kv/.md（同 stem 配对）
- 其余候选 reuse_existing（E259/E002/coinor-vol/limonp-1.0.2 草稿已覆盖）
- 路径 B（知识库扩展）成立：草稿与三方库归档同 PR 提交

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | header-only CMake 配方（package_type=header-library） |
| conandata.yml | 官方 URL + sha256 + 5 补丁声明 |
| patches/0001~0005 | 5 个 portability 补丁 |
| test_package/ | 消费者 5 组断言 + MANIFEST.yml（双口径台账） |
| reports/test-report.md | 上游测试报告（36 声明/35 执行/35 通过） |
| knowledge/drafts/DRAFT-limonp-0.6.1-cpp11-exact-match-tr1-fallback.* | 新知识草稿 |

## 注意事项

- 本机 inode 池耗尽限制：worktree 以 sparse-checkout（root + archives/l/limonp）物化
- W3/finish 本地验证须 `JUNK_PR_DIFF=pr.diff` 单包口径（full 模式会扫到 main 上其他库历史垃圾）
- conan-verify 的 E017 镜像注入会留下 conandata.yml.ghfast-bak，提交前须清理

**编译结束**: 2026-10-04
**最终状态**: published