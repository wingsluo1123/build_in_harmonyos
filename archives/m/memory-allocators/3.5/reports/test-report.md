# memory-allocators 3.5 verification report (R02)

## Environment

- OpenHarmony/HarmonyOS PC aarch64 real device
- Clang 15.0.4
- Conan 2.30.0 (OHOS 适配版)
- 构建系统: CMake（上游仅构建 benchmark 可执行文件；补丁 0001 新增静态库目标与 install 规则）

## 上游测试清点 (R51)

- 上游仓库 https://github.com/mtrebi/memory-allocators master（HEAD ad599a37）无 tests/
  目录、无 ctest 注册、无 pytest。
- 上游唯一可运行入口为 benchmark 主程序 `./main`（对 C/Linear/Stack/Pool/FreeList
  分配器执行分配/释放路径），实测运行 exit 0。
- 上游测试命令分析: `ctest -N` → 无注册测试。

## Verification

- `init-build memory-allocators 3.5`（master tarball, sha256 8c62d3ec...bff86622）: exit 0
- `lang-preflight memory-allocators 3.5` : exit 0 (task=cpp, detected=cpp)
- 手动 CMake 编译（cmake + make + ./main）: exit 0
- `conan-verify memory-allocators 3.5`: PASS（G0-G4 + L2/L4/L5）
- `finish memory-allocators 3.5 published`: W3 本地 CI（build_and_test.sh）通过

## R02 — CI fork-OOM 归因 (build 64417)

- 失败: `ci/conan/build_and_test.sh:116: fork failed: out of memory`（PR #13608, worker
  OpenHarmonyPCDeveloper-CI-018, 2026-09-29 12:14）
- 复现观测: 本机对同源命令（G0b 知识图谱检查, zsh）执行 exit 0 无 fork 失败；
  50x 纯 fork OK=50；内存 31.9GB 充足
- 根因定位: 失败行位于共享框架 G0b 知识图谱完整性检查段（任何当前库包构建之前），
  与 memory-allocators 源码/配方/测试无逻辑关联；属 CI worker 平台资源限制
- 交叉核验: 本地同源 zsh 重跑相同命令 PASS；未修改 ci/** 或共享框架
- 处置: 不将外部基础设施问题伪报为当前库缺陷；归因证据日志 ma-r02-ci-fork-oom-attr.log

## R02 — Review P2/P3 返工

### P2 复现（assert 在 Release/NDEBUG 下失效）
- r01 test.cpp 含 11 处 assert（含访问 protected 成员 `m_peak` 的断言），
  Release(NDEBUG) 下 assert 被预处理器移除后编译才通过 — assert 全部失效属实。
- 修复: 弃用 assert()，改为 NDEBUG 免疫的自定义 CHECK 宏（无论 NDEBUG 都实际执行校验）。

### P3 复现（failures 计数器死代码）
- r01 failures 恒为 0，失败分支从未被触发。
- 修复: CHECK 失败时真实 `++g_failures` 并打印失败详情，最终 exit_code 反映失败数。

### 修复后交付态验证
- Release(NDEBUG) 编译（clang++ -std=c++17 -DNDEBUG）: exit 0
  （日志 ma-r02-hohos-build-raw.log, sha256 ce706d40...）
- Release(NDEBUG) 运行: 21 checks / 0 failures / ALL PASS / exit 0
  （日志 ma-r02-hohos-run-raw.log, sha256 e546716c...）
- 负向证明（P3 失败链路）: 注入失败断言后 exit 1 且打印 `CHECK FAILED`，验证失败信号
  链路真实生效（日志 ma-negate.log, sha256 f3fe02ad...）

## HarmonyOS 专项测试（harmonyos_specific_test）

- 测试文件: test_package/test.cpp（消费者视角，实质调用 Linear/Stack/Pool/
  FreeList/CAllocator API 验证分配、对齐、释放；CHECK 宏 NDEBUG 免疫）
- 运行命令: `./test_memory-allocators`（Release/NDEBUG 语义与 CI 一致）
- 结果: CAllocator/Linear/Stack/Pool/FreeList 各段 OK，21 checks / 0 failures / ALL PASS
- 断言数: 21（R02 修正，替代原 14 处 NDEBUG 失效的 assert）
- exit_code=0；源码随 PR 交付（test_package/test.cpp 在 PR 文件列表中）

## test_package

- 测试用例: 1（test_memory-allocators）
- Passed: 1, Failed: 0, Skipped: 0

## Result

- 本地门禁全部通过（bootstrap / adapt / upstream_tests / test_package /
  harmonyos_specific_test / conan / finish / W2 / W3）
- R02 额外: CI fork-OOM 归因完成（平台资源限制，非当前库缺陷）；
  Review P2/P3 返工完成并负向验证失败信号链路
- 基线隔离: r01 已审计恢复（详见 /storage/Users/currentUser/tmp/ma-baseline-isolation-audit.json）；
  本轮未触碰基线/共享框架
