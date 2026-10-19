# newuoa-cpp 0.1.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-29
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos) / clang++
- 状态: published

## 编译步骤

```bash
# 官方源码: https://github.com/elsid/newuoa-cpp/archive/refs/tags/v0.1.2.tar.gz
# SHA-256: 660274f2ab2188bdf096c0ed0eefa8e10fe563e440064bc4e48ce547a8ef90a4
cmake -B build \
  -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang \
  -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++ \
  -DCMAKE_BUILD_TYPE=Release
cmake --build build -j4      # → libnewuoa.a
cmake --install build         # → include/newuoa.h, lib/libnewuoa.a, lib/cmake/newuoa, lib/pkgconfig/newuoa.pc

# conan 配方（W3 经 conan create 验证）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 直接传仓库页 URL 下载到 HTML | GitHub 仓库页不是归档 | 使用官方 release 归档 URL `/archive/refs/tags/v0.1.2.tar.gz` |
| 2 | conan-init 生成 `cpp_info.libs=["newuoa-cpp"]` | 模板按包名推断库名 | 修正为实际产物库名 `["newuoa"]`，并声明 cmake_target_name=`newuoa::newuoa` |
| 3 | test_package 模板 test.c 为空壳 | 模板占位 | 重写为真实消费者用例（调用 newuoa() 断言收敛 -144）并新增鸿蒙专项闭包测试 test_ohos.cpp |
| 4 | make jobserver mkfifo 报 Operation not permitted | HMDFS 不支持 mkfifo | 无影响，构建仍成功（cmake --build 内部降级） |

## 源码修改

无（上游 CMake 项目直接适配，无需补丁）。

## 依赖版本

无第三方运行时依赖（纯头文件 + 单源文件库）。

## 上游测试全量枚举台账（双口径）

### 源码全量枚举（官方 tag v0.1.2，共 10 个文件）

| 文件 | 类型 | 是否独立上游用例 | 说明 |
|------|------|------------------|------|
| CMakeLists.txt | 构建系统 | 否 | 仅 `add_library(newuoa)`，**无 enable_testing/add_test/CTest 注册** |
| LICENSE | 许可证 | 否 | MIT |
| cmake/Config.cmake.in | 框架文件 | 否 | CMake 包配置模板 |
| cmake/newuoa.pc.in | 框架文件 | 否 | pkg-config 模板 |
| include/newuoa.h | 公共头文件 | 否 | 导出 newuoa/newuoa_closure/newuoa_closure_const 三个 C 接口 |
| src/newuoa.cpp | 库源码 | 否 | NEWUOA 算法实现（Powell 信赖域） |
| src/example_function.c | 上游样例 | **否（样例，非测试用例）** | C 接口示例程序；已在本轮编译并运行，result=-144，退出码 0 |
| src/example_closure.cpp | 上游样例 | **否（样例，非测试用例）** | C++ 闭包接口示例程序；已在本轮编译并运行，result=-144，退出码 0 |
| .gitignore / .tarball-sha256 | 元数据 | 否 | 归档辅助文件 |

### 分类清点

- 用户测试源（TEST_CASE/测试框架真实用例）：**0**
- 框架头/源码（gtest/catch/doctest 等）：**0**
- 样例（example_*）：**2**（example_function.c、example_closure.cpp，属样例不计入独立用例）
- 基准（benchmark）：**0**
- fixture：**0**
- 测试脚本：**0**
- 构建目标：仅库目标 `newuoa`，**0 个测试可执行目标**

### 双口径统计

- `source_declared_total`（官方 tag 源码按可复制枚举规则发现的测试声明总数）：**0**
- `configured_executable_total`（当前 OHOS 配置实际实例化/注册的独立可执行用例数）：**0**（上游 CMakeLists 未启用任何测试框架或 CTest）
- `executed_passed_total`：**0**（无上游测试用例可执行）
- 失败数：**0**；未运行/未实例化数：**0**
- 全量通过率：**0/0**（上游无独立测试用例；上游两个样例已作为适配验证实际编译运行通过，result=-144，与预期一致）
- 逐项映射：源码无 TEST_CASE/宏/注册项 → 无预处理构建条件 → 无测试构建目标 → ctest -N 无注册项 → 无执行日志（样例运行日志见下）

### 样例实际运行证据（adaptation_validation，非独立用例但已运行）

```bash
$ clang++ -std=c++11 -I<prefix>/include src/example_closure.cpp <prefix>/lib/libnewuoa.a -o example_closure_ohos && ./example_closure_ohos
initial: [2] 0 -2.23607
final: [2] -4.47214 -2.23607
function_calls_count: 23
result: -144        # 退出码 0
$ clang -std=c11 -I<prefix>/include src/example_function.c <prefix>/lib/libnewuoa.a -lm -o example_function_ohos && ./example_function_ohos
initial: [2] 0.000000 -2.236068
final: [2] -4.472136 -2.236068
function_calls_count: 23
result: -144.000000  # 退出码 0
```

## 消费者用例与鸿蒙专项测试（test_package，conan create 内实际运行）

| 用例 | 源文件 | 调用的公开 API | 验证结果 |
|------|--------|----------------|----------|
| 消费者用例 | test_package/test.c | `newuoa()`（C 接口） | ctest 1/2 Passed，断言收敛 -144 ± 1e-3 |
| 鸿蒙专项测试 | test_package/test_ohos.cpp | `newuoa_closure_const()`（C++ 闭包接口） | ctest 2/2 Passed，断言收敛 0 ± 1e-4 (x=(3,-2)) |

> conan create 日志: reports/conan-create.log（两用例编译链接并运行，100% Passed）
> 消费者用例仅使用库已安装/导出的公开头文件 newuoa.h、公开 API 与正常链接目标（newuoa::newuoa），符合消费者可用性硬门禁。

## 验证结果

```bash
ohc-run.py conan-verify newuoa-cpp 0.1.2   # G0-G4 + L2/L4/L5 全部 PASS
```

## 交付物

| 文件 | 说明 |
|------|------|
| archives/n/newuoa-cpp/0.1.2/conanfile.py | Conan 配方（CMake 库，静态） |
| archives/n/newuoa-cpp/0.1.2/conandata.yml | 官方源 URL + SHA-256 |
| archives/n/newuoa-cpp/0.1.2/manifest.yaml | 版本 manifest |
| archives/n/newuoa-cpp/0.1.2/test_package/ | 消费者用例 + 鸿蒙专项测试（ctest 2/2 通过） |
| archives/n/newuoa-cpp/0.1.2/reports/conan-verify-report.md | verify 报告 |

## 注意事项

- 上游为纯库（无 CLI），产物仅 libnewuoa.a / 头文件，**不属于 CLI 库，不需要 commands.json**。
- 库名为 `newuoa`（产物 libnewuoa.a，CMake 目标 newuoa::newuoa），包名 newuoa-cpp 按上游仓库名。
- E092（CMake 不认识 HarmonyOS 平台）经 Conan CMakeToolchain 自动处理，conan create 实际通过。

## 知识候选台账与查重（task 流程第 6 步，提交前必做）

### 候选清点（非噪声项逐项四范围查重）

| 候选 | 真实错误/观察 | 根因 | 修复 | 验证 | 适用范围 | 正式图 index.tsv | knowledge/graph | knowledge/doc | knowledge/drafts | 结论 |
|------|--------------|------|------|------|----------|------------------|-----------------|----------------|-------------------|------|
| C1 | conan-verify G0 命中 E092（CMake 不识别 HarmonyOS 平台） | CMake 无 harmonyos/ohos platform module | Conan CMakeToolchain 自动映射 CMAKE_SYSTEM_NAME=HarmonyOS，无手写补丁 | conan create 通过（G2 PASS） | 所有 CMake 构建的库 | 已存在 E092 | E092.kv 已存在 | doc/E092.md 已存在 | 无新增草稿 | **复用已有知识（reuse_existing）** |
| C2 | conan-verify E017 注入 ghfast 镜像后残留 conandata.yml.ghfast-bak/.orig 备份，须手工恢复官方 URL 并清理 | 镜像注入的备份回滚机制 | 提交前核对 conandata.yml 为官方 HTTPS，删除 .orig/.ghfast-bak | 恢复前后 sha256 一致 | 含 GitHub 源的配方 | E017 已存在 | E017.kv 已存在 | doc/E017.md 已存在 | DRAFT-E323（.ghfast-bak 回滚缺陷）已存在 | **复用已有知识（reuse_existing）** |
| C3 | conan-init 生成 cpp_info.libs=["newuoa-cpp"] 按包名推断，实际产物 libnewuoa.a / newuoa::newuoa | conan-init CMake 模板按包名推断库名与 target 名 | package_info 修正 libs=["newuoa"] + cmake_file_name/cmake_target_name | conan create + 消费者 test_package 2/2 通过 | 包名与 CMake 目标名不一致的 CMake 库（repo 名带 -cpp/-c 后缀） | 无匹配 | E216/E221/E447 均为组件/传播类，不覆盖 | 无匹配 | DRAFT-400 为多包同名 clash，不覆盖 | **新增草稿 E429（new_draft）** |
| C4 | test_package 模板空壳 test.c（仅打印），触发 R34/PF3 空壳测试硬闸 | 模板占位 | 重写为真实消费者用例（newuoa()）并新增鸿蒙专项闭包测试 test_ohos.cpp | ctest 2/2 Passed | 所有 test_package | R34/PF3 为铁律非图谱条目，无 E 条目 | 无 | 无 | 部分草稿提及空壳测试（非本库专属） | **规则内修复，无新增知识（path_a_no_knowledge）** |

### 路径决定

- 候选 C1/C2：既有知识、图形、文档与草稿完整覆盖 → `reuse_existing`。
- 候选 C3：四范围查重均未命中、本库已用真实日志验证、可跨库复用（任何包名≠库名的 CMake 库）
  → **路径 B（知识库扩展）建立同 stem 草稿** `knowledge/drafts/E429-draft-28FE.kv` + `.md`
  （knowledge 草稿与三方库归档进入同一 PR）。
- 候选 C4：框架铁律 R34/PF3 已强制，本库按规则修复即可，无独立知识增量。

### C3 七轴查重（E429）

- `exact_duplicate`: false（无条目按包名推断 libs 的 conan-init 缺陷）
- `causal_duplicate`: false（根因不同：非组件传播、非多包同名 clash）
- `trigger_overlap`: partial（E321 同用 set_property 修正 target 名，但触发入口不同：E321 是头文件库迁移/多包 clash）
- `solution_overlap`: partial（修正手段涉及 cmake_target_name，机制类似 E321）
- `combination_novelty`: true（"conan-init 模板生成缺陷 × 包名≠库名"组合未被既有条目覆盖）
- `boundary_novelty`: true（边界=repo 名带 -cpp/-c 后缀或与 project() 目标名不一致的 CMake 库）
- `test_migration_novelty`: false（非测试迁移类）
- 关系：`similar_to: E321`；`reuse_existing`（C1/C2）/`new_draft`（C3）/`path_a_no_knowledge`（C4）
---

**编译结束**: 2026-09-29 03:45
**最终状态**: published
