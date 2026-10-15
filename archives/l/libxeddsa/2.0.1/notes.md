# libxeddsa 2.0.1 适配笔记

## 编译环境
- 构建系统: cmake（根 CMakeLists.txt + ref10/CMakeLists.txt）
- 编译日期: 2026-09-28
- 编译器: clang 15.0.4 (aarch64-linux-ohos)
- 状态: built（W3 本地 CI 通过，.ci-result.json exit_code=0）

## 依赖
- libsodium/1.0.22（ohpcd 制品仓，静态变体；上游 find_package(Sodium REQUIRED)）

## 编译步骤
1. CMake 配置（探索阶段本机）：`cmake .. -DCMAKE_SYSTEM_NAME=Linux ... -Dsodium_USE_STATIC_LIBS=ON`
   —— 因 CMake 不识别 HarmonyOS 平台（无 Platform/HarmonyOS.cmake），ref10 的
   `if (UNIX)` 门禁报 "Unsupported operating system"，先用 Linux 语义验证上游质量。
2. `make -j4` → 静态库 libxeddsa.a + 3 个测试可执行，全部构建成功。
3. `make install DESTDIR=...` → staging 隔离验证。
4. `ctest` → xeddsa_test_static / kernelrandombytes_test_static / kernelrandombytes_test_dynamic
   3/3 全过（上游 4 个独立用例 100%）。
5. Conan 配方阶段：conan-verify G0-G4 + L2/L4/L5 全过；conan create 的 test_package
   实际运行消费者测试与鸿蒙专项测试 2/2 通过。
6. finish：W2 结构完整、W3 本地 CI 通过（JC_RESULT=pass, 1/1, 100%）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | ref10/CMakeLists.txt configure 失败 "Unsupported operating system (neither UNIX nor Windows)" | CMake 不识别 HarmonyOS 为 UNIX，`if(UNIX)` 门禁为假 | patches/0003: 平台检查加 `OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS"` |
| 2 | FindSodium.cmake 报 "this platform is not supported by FindSodium.cmake" | Find 模块 UNIX 分支 `elseif(UNIX)` 在 HarmonyOS 下不命中，落入 unsupported 分支 | patches/0002: 平台分支加 HarmonyOS 判定（UNIX 分支 + else 分支 IMPORTED_LOCATION 设置处） |
| 3 | conan create 中 imported target "sodium" 缺 IMPORTED_LOCATION，生成 sodium-NOTFOUND | FindSodium.cmake 内部 X_LAST 缓存重置逻辑在首次 configure 时 unset 掉 Conan toolchain 注入的 sodium_LIBRARY_* CACHE 变量 | patches/0002: 注入路径存在时跳过缓存重置块 |
| 4 | 静态 libsodium 下 xeddsa_dynamic 目标 duplicate symbol: randombytes（fastrandombytes vs libsodium） | 上游自带 ref10/fastrandombytes 定义 randombytes，动态链接系统共享 libsodium 时无冲突；OHOS 制品仓仅静态 libsodium → 冲突 | patches/0001: 新增 XEDDSA_BUILD_DYNAMIC 选项，关闭 dynamic 目标（配方中置 OFF） |
| 5 | W3 JC junk check 拦截 4 个其他库已跟踪空文件（cloog/kics/thc 的 .build-closed/.staging-verified） | 这些文件在 origin/main 基线中已被跟踪，junk_check full 模式（git ls-files）命中 | 基线隔离复验：记录路径+隔离前 SHA-256 → git rm --cached 临时隔离 → 复跑 W3 通过 → git add -f 原样恢复 → 恢复后 SHA-256 一致；不修改/不提交该基线文件 |
| 6 | 探索编译需注入 libsodium 路径 | FindSodium.cmake 靠 pkg-config/find_path/find_library 定位，Conan 构建环境默认搜不到 | 配方 generate() 用 `self.dependencies["libsodium"]` 显式注入 sodium_INCLUDE_DIR / sodium_LIBRARY_RELEASE / sodium_LIBRARY_DEBUG |

## 源码修改（补丁）
- patches/0001-CMakeLists.txt.patch: XEDDSA_BUILD_DYNAMIC 选项（静态 libsodium 下 dynamic 目标 randombytes 重复符号）
- patches/0002-FindSodium.cmake.patch: HarmonyOS 平台分支 + 注入路径跳过缓存重置 + IMPORTED_LOCATION 设置
- patches/0003-ref10-CMakeLists.txt.patch: UNIX 门禁接受 HarmonyOS

## 验证结果
```bash
# 上游测试（本机探索编译，ctest 3/3）
ctest --output-on-failure          # xeddsa_test_static/kernelrandombytes_test_static/kernelrandombytes_test_dynamic 全过
# 上游 4 个独立用例: test_signing / test_conversion_uniqueness / test_pub_derivation / kernelrandombytes
# 全量通过率 4/4 = 100%（source_declared_total=4, executed_passed_total=4）
# 鸿蒙专项: test_package/ohos_specific_test.c 5/5 PASS（随机源探测/公钥转换往返/x25519/签名验签）
# 消费者: test_package/test.c（xeddsa_init/seed_to_ed25519_pub/ed25519_seed_sign/ed25519_verify 含篡改负例）
# conan-verify: G0-G4 全过; W3 本地 CI: JC/L0/L1 pass, 1/1, 100%
```

## 知识候选台账（knowledge_candidate_ledger）

### 候选 C1: CMake 平台门禁 `if (UNIX)` 在 HarmonyOS 下失效（ref10 + FindSodium.cmake 双处）
- 真实错误: ref10/CMakeLists.txt:45 "Unsupported operating system (neither UNIX nor Windows)"；FindSodium.cmake:230 "this platform is not supported"
- 根因: CMake 无 Platform/HarmonyOS.cmake，`UNIX` 变量为假，所有 `if(UNIX)/elseif(UNIX)` 门禁不命中
- 修复: `if (UNIX OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")`（0002/0003 补丁）
- 验证: conan-verify G2 通过；W3 通过
- 适用范围: 任何 CMake 工程/Find 模块以 `if(UNIX)` 或平台分支路由、在 HarmonyOS 上配置失败的场景
- 查重（含四范围 full scan，drafts/ 后发现同库既有条目）:
  - **既有条目: DRAFT-libxeddsa-2.0.0-cmake-system-name-harmonyos-unix-gate（同库 2.0.0 同根因、同错误特征、同触发表达式）**
  - exact_duplicate: **是**（同库、同错误签名 "Unsupported operating system"、同 `if(UNIX)` 触发；
    2.0.0 方案为 tc.variables 声明 CMAKE_SYSTEM_NAME=Linux，本轮以 patch 门禁方式实现——
    方案变体属同一知识条目的实现差异，非独立新增差异）
  - causal_duplicate: 是（完全同根因：OHOS 适配版 CMakeToolchain 映射
    CMAKE_SYSTEM_NAME=HarmonyOS，vanilla CMake 无平台模块）
  - trigger_overlap: 高（E092/E140/E267 + 2.0.0 草稿同特征）
  - solution_overlap: 高（2.0.0 草稿 solution 家族已含 declare-Linux 与 patch 变体）
  - combination_novelty: 低（无新组合）
  - boundary_novelty: 低（2.0.0 草稿 affected_scope 已覆盖 ref10 与 Find 模块双处）
  - test_migration_novelty: 低
- 关系: similar_to=[DRAFT-libxeddsa-2.0.0-cmake-system-name-harmonyos-unix-gate, E092, E140, E267]；caused_by=E092 家族
- **结论: reuse_existing（复用 2.0.0 既有草稿，不建新草稿）**

### 候选 C2: Find 模块内部 X_LAST 缓存重置逻辑清掉 Conan toolchain 注入的库路径变量
- 真实错误: conan create generation 报 CMP0111 "IMPORTED_LOCATION or IMPORTED_IMPLIB not set for imported target 'sodium'"，make 报 "No rule to make target 'sodium-NOTFOUND'"
- 根因: FindSodium.cmake 用 `sodium_USE_STATIC_LIBS_LAST` 做变更追踪，首次 configure（_LAST 未定义）时 unset 全部 sodium_LIBRARY_* CACHE 变量，清掉 toolchain 注入的路径
- 修复: 0002 补丁——`DEFINED sodium_LIBRARY_RELEASE AND NOT MATCHES -NOTFOUND` 时跳过缓存重置
- 验证: conan-verify G2 通过（之前连续 2 轮失败定位到此处）
- 适用范围: 任何"Find 模块自带 X_LAST 缓存重置 + Conan toolchain 显式注入库路径"的库
- 查重（含四范围 full scan，drafts/ 后发现同库既有条目）:
  - **既有条目: DRAFT-libxeddsa-2.0.0-find-sodium-cache-unset-equal-guard（同库 2.0.0 同根因：EQUAL 看门狗每次 configure unset sodium_* CACHE；推荐方案
    feed-cmake-include-library-path，fallback patch-find-module-guard——本轮的跳过重置
    守卫即其 fallback 实现）**
  - exact_duplicate: **是**（同库、同 FindSodium.cmake EQUAL 看门狗、同 unset 机制；
    2.0.0 草稿 fallback_approach=patch-find-module-guard 已明确列出本类修复，无独立新增）
  - causal_duplicate: 是（完全同根因）
  - trigger_overlap: 高（与 2.0.0 草稿 error_signature 同含 NOTFOUND/Sodium REQUIRED）
  - solution_overlap: 高（2.0.0 草稿已列两种方案，本轮实现为其 fallback）
  - combination_novelty: 低
  - boundary_novelty: 低
  - test_migration_novelty: 低
- 关系: similar_to=[DRAFT-libxeddsa-2.0.0-find-sodium-cache-unset-equal-guard, E376]
- **结论: reuse_existing（复用 2.0.0 既有草稿，不建新草稿）**

### 候选 C3: 静态依赖库符号冲突 → 上游同时构建 static+shared 时 shared 目标失败
- 真实错误: ld.lld "duplicate symbol: randombytes"（fastrandombytes.c vs libsodium randombytes.o）
- 根因: 上游自带 ref10/fastrandombytes 定义 randombytes；共享 libsodium 时无冲突（符号 interpose），静态 libsodium 时强符号重复
- 修复: XEDDSA_BUILD_DYNAMIC 选项关闭 dynamic 目标（0001 补丁 + 配方 generate() OFF）
- 验证: conan-verify G2 通过，静态库 + 测试全绿
- 查重（含四范围 full scan，归档 + drafts/ 后确认既有处理）:
  - **既有处理: archives/l/libxeddsa/2.0.0-20231128.d725c81（同库 2.0.0 归档：
    patch 0001-cmake-gate-shared-targets-on-build_shared_libs.patch 以
    BUILD_SHARED_LIBS 门控动态目标，notes.md 记录"上游静态+动态并行、
    libxeddsa.so 需吸收 ohpcd 静态非 PIC libsodium.a 有重定位风险，
    补丁门控共享目标"——与本轮 XEDDSA_BUILD_DYNAMIC 门控为同一修复模式）**
  - exact_duplicate: **是**（同库、同 shared 目标与静态依赖冲突问题、同门控修复模式；
    本轮的独立 option 命名属实现变体，非新增独立知识）
  - causal_duplicate: 是（完全同根因：静态依赖 + 上游双目标构建）
  - trigger_overlap: 高（与 2.0.0 归档 notes 同问题）
  - solution_overlap: 高（同为 CMake 目标门控）
  - combination_novelty: 低
  - boundary_novelty: 低
  - test_migration_novelty: 低
- 关系: similar_to=[archives/l/libxeddsa/2.0.0-20231128.d725c81, E163]; caused_by=静态依赖符号冲突
- **结论: reuse_existing（复用 2.0.0 归档既有方案，不建新草稿）**

### 候选 C4: W3 JC 拦截其他库已跟踪基线文件（流程类，非技术知识）
- 处理: 按 SKILL 基线隔离协议（记录路径+SHA-256 → 隔离 → 复跑 → 恢复）完成，未修改/未提交基线文件
- 查重: 与 E291（repository_baseline_blocked）流程覆盖；SKILL §基线隔离 已明确规则 → 不建新草稿（path_a_no_knowledge 对待）

### 修改记录
- 2026-09-28 注意: 初次查重仅扫 index.tsv/graph/doc，未扫 drafts/ 同库条目；后经
  drafts/ 范围核对发现 libxeddsa 2.0.0 既有 3 条草稿与 2.0.0 归档方案完整覆盖
  C1/C2/C3，已删除本轮误建的两条重复草稿（DRAFT-libxeddsa-cmake-harmonyos-
  platform-gate、DRAFT-libxeddsa-static-libsodium-dynamic-dup-symbol），
  改按 reuse_existing 处理。

## 路径决定（path_decision，最终修订）
- 候选 C1/C2/C3: 经四范围（index.tsv / knowledge/doc/ / knowledge/graph/ /
  knowledge/drafts/）full scan 后发现同库 2.0.0 既有知识完整覆盖，七轴显示
  exact_duplicate=是 / combination_novelty=低，无独立新增差异可跨库复用
  → **reuse_existing（复用既有知识，路径 A 对待，不建新草稿）**
- 候选 C4: 流程规则已覆盖 → 复用既有知识（无新草稿）
- 决定: `reuse_existing`（PR 前缀按任务头 【知识库扩展】）

## 交付物
- conanfile.py / conandata.yml / test_package（test.c 消费者 + ohos_specific_test.c 鸿蒙专项）/ patches 0001-0003
- reports/test-report.md（上游台账+双口径+鸿蒙专项+消费者）
- 知识沉淀: 本轮候选经四范围查重确认与同库 2.0.0 既有草稿完整重复 → reuse_existing，
  复用 knowledge/drafts/DRAFT-libxeddsa-2.0.0-* 三条草稿，不新建草稿

---

**编译结束**: 2026-09-28 17:20
**最终状态**: built
