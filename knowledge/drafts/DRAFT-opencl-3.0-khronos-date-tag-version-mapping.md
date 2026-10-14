# Khronos 规范头文件库的版本映射与 header-only 适配（草案）

> 草稿编号：DRAFT-opencl-3.0-khronos-date-tag-version-mapping
> 来源：opencl 3.0 适配（KhronosGroup/OpenCL-Headers，官方 tag v2026.05.29）
> 生成日期：2026-10-04

## 问题描述

Khronos 系列头文件库（以 OpenCL-Headers 为例）的 git tag 采用**日期型命名**
（`v2026.05.29`、`v2025.07.22` 等），而 OpenCL API 的版本是**规范版本号**
（3.0、3.1）。任务系统按规范版本命名任务（`opencl 3.0`）时，直接拼接
`https://github.com/KhronosGroup/OpenCL-Headers/archive/refs/tags/v3.0.tar.gz`
会得到 **HTTP 404**：

```
curl -sSL -o /dev/null -w '%{http_code}\n' \
  https://github.com/KhronosGroup/OpenCL-Headers/archive/refs/tags/v3.0.tar.gz
→ 404
```

即：**任务版本号与上游 tag 体系不对应**。若强行按规范版本号找 tag 则货源不可得；
若丢弃任务版本号又会破坏任务身份与分支命名（`feat/opencl-3.0`）。

## 根因

- OpenCL-Headers 仓库没有任何 `v3.0` 风格的 tag，tag 全为日期型（GitHub API：
  17 个 tag，全部 `vYYYY.MM.DD`）。
- OpenCL 规范版本（3.0）是 API 规范代号，不是该仓库的发布 tag。
- 但上游 `CMakeLists.txt` 中 `project(OpenCLHeaders VERSION 3.0 ...)` 恰好把
  规范版本写进了 CMake 工程版本号——这是任务版本号最权威的官方佐证。

## 解决方案

1. **货源选择**：查询上游 tag 列表，无同名 tag 时取**官方最新日期型 tag**
   的 archive tarball 为源，独立 `sha256sum` 核验后写入 `conandata.yml`。
2. **版本号保持**：Conan/归档版本号保持任务指定的规范版本（`3.0`），
   在 `notes.md` 明确"任务版本号 ↔ 官方 tag"的映射关系及其依据
   （CMake `project VERSION 3.0`）。
3. **header-only 打包**：`package_type="header-library"`，`package()` 把
   `CL/*.h` 复制到 `include/CL/`，`package_info()` 仅 `includedirs=["include"]`；
   `export_sources()` + `apply_conandata_patches` 保证配方完整性（G1）。
4. **测试门禁**：
   - 上游测试按 `add_header_test` 宏枚举规则清点：每头文件 × 8 版本（
     100/110/120/200/210/220/300/310）× 选项（≥300 额外 +CL_ENABLE_BETA_EXTENSIONS）
     = 每头 10 用例；lang_c 18 头 + lang_cpp 17 头 = **350**。
   - `test_package` 消费者真实 include `<CL/opencl.h>` 并断言宏值（R34 反空壳）。
   - 鸿蒙专项测试 `tests/ohos_special_test.c`：`-DCL_TARGET_OPENCL_VERSION=300`
     编译运行，断言版本宏/枚举值/`__OHOS__` 平台检测/类型大小。
   - 非 CLI 库不得伪造 `commands.json`（R38 仅 CLI 库需要）。

## 验证

opencl 3.0 本轮实测：

| 门禁 | 结果 |
|------|------|
| 货源 | v3.0.tar.gz 404 → 采用官方 v2026.05.29，sha256 d9e6c483...（与既有 opencl-headers/2026.05.29 归档同源） |
| lang-preflight | task=cpp detected=cpp（R47 通过） |
| 上游测试 | ctest 350/350 (100.0%) |
| 鸿蒙专项 | 8/8 断言通过 |
| 消费者 | test_package 编译+运行 PASSED |
| conan-verify | G0-G4/L2/L4/L5 全 PASS |
| W3 本地 CI | JC_RESULT=pass, 100% (1/1) |

## 适用边界

- **适用**：Khronos 生态头文件库（opencl-clhpp-headers、OpenCL-ICD-Loader 的 header
  依赖）及一切"任务版本号 ≠ 上游 tag"的库；日期型 tag 仓库的版本映射。
- **反例/不适用**：上游存在与任务版本号同名 tag 的情况（直接映射即可）；
  任务版本号纯属任务系统自造且 CMake/上游均无法佐证时，按任务约束执行并如实申报。

## 查重差异

- `E470`（cppitertools tag-as-provenance-source）：覆盖"上游 conanfile version
  滞后于官方 tag 时以官方 tag 为准"，**partial overlap**——本候选是"任务版本号
  无对应 tag 时以官方最新 tag 为源且 Conan 版本保持任务号"，触发与决策不同。
- `E035/E257/E321/E322/E307/E399/build-systems.md §12`：覆盖 header-only 通用
  配方模式，本候选复用其结论，新增**日期型 tag 映射决策 + add_header_test
  枚举规则**（每头 ×8 版本 ×选项 = 10 用例），可跨库迁移（clhpp/ICD-Loader）。
- 结论：**partial overlap + 新增差异** → new_draft（本文件）。