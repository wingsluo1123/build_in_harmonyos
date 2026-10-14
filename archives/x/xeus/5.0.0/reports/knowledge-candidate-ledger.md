# xeus 5.0.0 知识候选台账（knowledge_candidate_ledger）

- task_id: xeus-5.0.0-r01-pc3-5-20261009T094604Z
- 生成时间: 2026-10-09
- 本库路径: archives/x/xeus/5.0.0（PR 前缀 【高难度挑战】）

## 候选清单与四范围查重

### C1: CMake 不识别 OHOS 平台（"System is unknown to cmake"）→ 归一化 CMAKE_SYSTEM_NAME

- 真实错误: `System is unknown to cmake, create: Platform/HarmonyOS to use this system`（configure 阶段多条警告）；
  本库按仓库通行做法归一化 `CMAKE_SYSTEM_NAME=Linux`。
- 根因: CMake 无 HarmonyOS 平台模块，OHOS 三态（os=OHOS）无法匹配任何已知平台。
- 修复: conanfile.py generate() 中 `tc.cache_variables["CMAKE_SYSTEM_NAME"]="Linux"` + `CMAKE_SYSTEM_PROCESSOR="aarch64"`。
- 验证: conan create 通过（libxeus.a + test_package 2/2）；上游 51 用例全过。
- 适用范围: 所有 CMake 系 OHOS 适配。
- 查重结果:
  - 正式条目: **E092 / E140 / E267 完整覆盖**（error_signature 均含 "System is unknown to cmake"，
    rec_approach=add-harmonyos-cmake-detection，含 OHOS/HarmonyOS 双拼写归一化建议）
  - 图谱: index.tsv 命中同族 3 条；signal=1（E092）
  - doc: doc/E092.md / doc/E140.md / doc/E267.md 已配套
  - 草稿: 无新增必要
- 判定: **完整重复 → 复用已有知识，不建草稿（走路径 A 组件的知识复用）**

### C2: conandata.yml 注释中的裸仓库 URL 前缀 → pre-download 子串 replace 污染 sources.url

- 真实错误: `NotADirectoryError: [Errno 20] Not a directory: '.../predl_cache/90aa7908_xeus/archive/refs/tags/5.0.0.tar.gz'`
  （W3 build_and_test.sh conan create 失败）。
- 根因: ci/conan/build_and_test.sh 的 pre-download 机制对 conandata.yml 逐条 URL 做
  `content.replace(url, f'file://{local_path}')`（子串替换）。若 conandata.yml 注释中出现
  裸仓库主页 URL（https://github.com/org/repo），它是真实 sources.url
  （…/org/repo/archive/refs/tags/v.tar.gz）的**前缀子串**，被 replace 误伤成 file:// 目录路径；
  conan get() 走 gh-proxy 镜像失败且路径非目录 → NotADirectoryError。
- 修复: conandata.yml 注释移除裸 URL（只保留"官方 tag x.y.z"文字描述）；预下载缓存 seen 前清理。
- 验证: 修复后 W3 build_and_test.sh 通过（.ci-result.json exit_code=0）；conan create 全绿。
- 适用范围: 任何 conandata.yml 注释含裸 URL 且 URL 是 sources.url 前缀的配方（全仓通用 CI 交互）。
- 查重结果:
  - 正式条目: **E333 部分覆盖**（同门禁、同 predl_cache 机制，但 E333 根因是 PyPI 连字符
    URL 正则截断，非"注释裸 URL 前缀子串污染"；本候选是新错误路径）
  - 图谱: index.tsv 命中断言类 predl 条目（E333 signal=1）
  - doc: doc/E333.md 只讲截断场景
  - 草稿: 无同名草稿
- 判定: **部分覆盖且有新增差异（可跨库复用、已由本轮真实日志验证）→ 建 DRAFT（路径 B 知识组件）**

### C3: test_package 消费者必须显式持有被测包公开头依赖的 conan 依赖（nlohmann_json/uuid）

- 真实错误: `test_package 编译 fatal error: 'nlohmann/json.hpp' file not found`（conan create test 阶段）。
- 根因: xeus 公开头 xjson.hpp/xhelper.hpp 直接 `#include <nlohmann/json.hpp>`；CMakeDeps 对
  "被测试包自身" 只生成其直接目标，若测试消费者不显式 requires 该头文件依赖，include 目录不注入。
  同时 xeusConfig 导出目标为无命名空间 `xeus`/`xeus-static`，而 CMakeDeps 生成 `xeus::xeus`，
  test_package 需兼容双目标名。
- 修复: test_package/conanfile.py requirements() 显式 `self.requires("nlohmann_json/3.12.0")`
  + `uuid/2.40.1`；CMakeLists 链接目标选择 `xeus::xeus` > `xeus` > `xeus-static`。
- 验证: conan create test 阶段 2/2 通过（消费者 + 鸿蒙专项）。
- 适用范围: 公开头带第三方 include 的 C++ 库（nlohmann_json 族）的 test_package 编写；
  CMake 导出无命名空间目标的库。
- 查重结果:
  - 正式条目: **E216 部分覆盖**（同为 CMakeDeps 传播问题，但 E216 是组件 INTERFACE include
    失效 + GLOB 兜底，本候选是"consumer 显式 requires + 目标名兼容"）
  - 图谱: index.tsv 命中 E216/E221（signal=2/3，相关不重复）
  - doc: doc/E216.md / doc/E221.md
  - 草稿: DRAFT-13532-getdns-1.7.3-cmakedeps-prefer-config（不同场景：prefer-config vs find-module）
- 判定: **部分覆盖且存在新增差异（双目标名兼容 + 显式持有公开头依赖），本轮真实验证 → 建 DRAFT（可并入 C2 草稿对）**

## 关系字段（C2/C3 草稿）

- C2: similar_to=null（E333 同类门禁不同根因）、caused_by=null、prerequisite_of=null、conflicts_with=null
- C3: similar_to=null（E216 同域不同机制）、caused_by=null、prerequisite_of=null、conflicts_with=null

## 路径初判决定

- **path_b_new_draft**: C2 + C3 为已验证、可跨库复用、查重未命中/部分覆盖且存在新增差异的候选 → 建立
  `DRAFT-xeus-5.0-*` 的 .md/.kv 配对草稿。
- C1 完整重复 → 复用既有知识（E092/E140/E267），不建草稿。
- 注意：本任务为《高难度挑战》型，PR 前缀固定为 【高难度挑战】；knowledge 组件草稿随本库归档文件
  进入同一 PR（不另建独立知识库 PR）。