# opencl 3.0 适配笔记

## 编译环境
- 构建系统: headeronly（CMake 声明 project VERSION 3.0，纯头文件无编译）
- 编译日期: 2026-10-04
- 编译器: clang/clang++ 15.0.4 (aarch64-linux-ohos)
- 状态: built

## 上游信息
- 名称：opencl（OpenCL-Headers，Khronos Group）
- 任务版本：3.0（OpenCL 规范版本）
- 上游仓库：https://github.com/KhronosGroup/OpenCL-Headers
- 上游 tag：v2026.05.29（上游无 v3.0 tag，tag 均为日期型；CMake project VERSION 3.0 与任务版本一致）
- 源码包：https://github.com/KhronosGroup/OpenCL-Headers/archive/refs/tags/v2026.05.29.tar.gz
- sha256：d9e6c48357de5002da11ce45de600e0c3ffe6ab4f628a3b9fe2b38603161658a
- 许可证：Apache-2.0

## 版本映射说明
任务版本 "3.0" 是 OpenCL API 规范版本；上游 OpenCL-Headers 仓库无 v3.0 tag（
`curl https://github.com/KhronosGroup/OpenCL-Headers/archive/refs/tags/v3.0.tar.gz` → 404），
tag 体系为日期型（v2026.05.29 最新）。本适配以官方最新 tag v2026.05.29 tarball 为源
（SHA-256 核验一致），Conan 版本号保持任务指定的 3.0（CMake project VERSION 3.0 佐证）。

## 编译步骤
1. init-build opencl 3.0 --url=<官方 v2026.05.29 tarball>（下载、.orig/.work 双轨、骨架）
2. 源码审计：SHA-256 独立复算一致、无 file:///缓存/绝对路径污染、纯头文件库（非 CLI，无 commands.json）
3. lang-preflight：task=cpp detected=cpp（通过，R47）
4. 上游测试：cmake configure（-DOPENCL_HEADERS_BUILD_TESTING=ON）+ build + ctest → 350/350 通过
5. 鸿蒙专项测试 tests/ohos_special_test.c：clang -DCL_TARGET_OPENCL_VERSION=300 编译运行 → 8/8 通过
6. conan-init + conan-verify（G0-G4/L2/L4/L5 全 PASS）
7. finish built：W2 结构 + R36 依赖（无依赖）+ W3 conan create PASS（JUNK_PR_DIFF 单包口径）
8. 基线隔离复验：W3 JC full 模式误扫 cloog/kics 其他库存量垃圾 → 单包口径复跑 PASS，审计见 reports/baseline-isolation-audit.json

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游无 v3.0 tag（404） | OpenCL-Headers 用日期型 tag；规范版本 3.0 非发布 tag | 用官方最新 tag v2026.05.29 tarball + SHA-256 核验，Conan 版本保持 3.0 |
| 2 | conan-verify G1 缺 export_sources/补丁调用 | headeronly 模板生成不完整 | 补 export_sources() 方法与 apply_conandata_patches |
| 3 | conan-verify E017 残留 conandata.yml.ghfast-bak | 镜像注入后备份残留 | 提交前清理，JC1 不拦截 |
| 4 | W3 JC full 模式误扫其他库存量垃圾（cloog/kics .build-closed/.staging-verified） | 本地无 origin/main 差异时回退 full 扫描整仓 | JUNK_PR_DIFF=pr.diff 单包口径复跑 + 基线隔离审计（pre==post SHA-256） |

## 源码修改
无（纯头文件库，无补丁）

## 依赖版本
无第三方依赖（header-only）

## 验证结果
- 上游测试：350/350 (100.0%) 通过（lang_c 18×10 + lang_cpp 17×10）
- 鸿蒙专项：8/8 断言通过
- 消费者：test_package test.c 编译+运行 PASSED
- conan-verify：G1/G2/G3/G4/L2/L4/L5 全 PASS
- W3 本地 CI：JC_RESULT=pass, L0_RESULT=pass, 100% (1/1)

## 知识候选台账（knowledge candidate ledger）

### 候选 C1：Khronos 规范头文件库的"任务版本号 vs 日期型 tag"映射 + header-only 打包 + add_header_test 测试枚举

- 真实错误：上游无 v3.0 tag（v3.0.tar.gz 404），任务版本号无法直接映射到 tag
- 根因：OpenCL-Headers 采用日期型 tag（v2026.05.29 等），OpenCL 规范版本（3.0）是 API 规范版本而非发布 tag；任务以规范版本命名
- 修复：以官方最新 tag tarball 为源 + SHA-256 独立核验；Conan 版本保持任务号（CMake project VERSION 佐证）；notes 记录映射
- 验证：350/350 上游测试 + 8/8 鸿蒙专项 + 消费者用例 + conan-verify 全门禁 + W3 全通过（本库实测证据）
- 适用范围：Khronos 生态（opencl-clhpp-headers、OpenCL-ICD-Loader 等）及一切"规范版本号 ≠ 发布 tag"的头文件库
- 四范围查重：
  - 正式知识 doc/：E470（cppitertools tag-as-provenance-source）部分覆盖 tag-vs-version 原则，但触发不同（上游 conanfile version 滞后 vs 无对应 tag）
  - 图谱 graph/：E035/E257/E321/E322/E307/E399 覆盖 header-only 通用模式；无 opencl 专门条目
  - 草稿 drafts/：无 opencl 草稿；DRAFT-E323（ghfast-bak rollback）覆盖 E017 残留分支
  - operations/build-systems.md §12：header-only 模板已覆盖（R34/R51 适用）
- 七轴查重：
  - exact_duplicate: false（无 opencl 条目）
  - causal_duplicate: false（E470 触发不同）
  - trigger_overlap: partial（E470 同属 tag-vs-version 域）
  - solution_overlap: partial（header-only 打包复用 E321/E470；映射决策新增）
  - combination_novelty: true（OpenCL-Headers 规范版本映射 + add_header_test 枚举组合）
  - boundary_novelty: true（"任务版本号无对应 tag 时以官方最新 tag 为源"边界）
  - test_migration_novelty: true（add_header_test 宏枚举 = 每头 ×8 版本 ×2 选项 = 10 用例，可迁移 clhpp/ICD-Loader）
- 关系：similar_to E470；prerequisite_of opencl-clhpp-headers 适配
- 决定：**new_draft**（见 knowledge/drafts/DRAFT-opencl-3.0-khronos-date-tag-version-mapping.kv/.md）

### 候选 C2：W3 JC full 模式误扫其他库基线垃圾 → JUNK_PR_DIFF 单包口径

- 真实错误：W3 JC full 模式扫描整仓，命中其他库存量垃圾（cloog/kics）
- 根因：本地分支与 origin/main 无差异时 junk_check 回退 full 模式
- 修复：JUNK_PR_DIFF=pr.diff 单包口径复跑 + 基线隔离审计（pre==post SHA-256、diff/staged 不含基线路径）
- 验证：本库 W3 复跑 exit_code=0 通过（.ci-result.json）
- 适用范围：所有本地 W3 遇到 full 模式误扫的执行端
- 查重：oh-executor SKILL 已内建基线隔离复验规则（任务级规程），E291 覆盖 repository-baseline-blocked 回报；非三方库适配知识
- 决定：**path_a_no_knowledge**（属执行端操作规程，不建草稿；记忆已记录）

## 注意事项
- conan-verify 每次 E017 注入都会重建 conandata.yml.ghfast-bak，提交前必须清理
- 本地 W3 必须用 JUNK_PR_DIFF=pr.diff 单包口径（full 模式误扫其他库基线）
- 纯头文件库无需 commands.json（R38 仅 CLI 库需要）

---

**编译结束**: 2026-10-04 16:38
**最终状态**: built
